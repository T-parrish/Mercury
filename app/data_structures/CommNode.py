import asyncio
import pprint
import string
import re
import base64

from typing import TypeVar, List, Callable, Dict, Generator, Union
from abc import ABCMeta, abstractmethod

from collections import Counter
from datetime import datetime, date

from bs4 import BeautifulSoup
from spacy.lang.en import English
from spacy.lang.en.stop_words import STOP_WORDS

from . import poc_set, target_set, Routine
from .Entity import POC, Entity
# from helpers.clock import noArgClock

M = TypeVar("M")
nlp = English()

class CommNode:
    '''
    Attributes:
    -----------
        labels: List[str]
            a list of labels for each message
        mimetypes: List[str]
            a list of mimetypes included in the message
        subject: str
            Subject of the message being parsed
        html_body: str
            Text parsed from raw message with mimetype == text/html
        plaintext_body: str
            Text parsed from raw message with mimetype == text/plain
        entities: List[Entity]
            Named tuple that holds entity data to be stored in Postgres
        date: DateTime
            Parsed DateTime object for message
        ip_address: str
            ip address for proxy the message was sent through
        msg_id: str
            Gmail API message ID
        thread_id: str
            Gmail API thread ID
        keywords: Counter
            Word frequency counter object
    '''

    __slots__ = ['labels', 'mimetypes', 'subject',
                 'html_body', 'plaintext_body', 'entities',
                 'date', 'ip_address', 'msg_id', 'thread_id', 'keywords']

    def __init__(self,
                 labels: List[str] = list(),
                 mimetypes: List[str] = list(),
                 subject: str = '',
                 html_body: str = '',
                 plaintext_body: str = '',
                 entities: List[Entity] = list(),
                 date: datetime = datetime.now(),
                 ip_address: str = '',
                 msg_id: str = '',
                 thread_id: str = '',
                 keywords: Dict[str, int] = {},
                 ) -> None:

        self.labels = labels
        self.mimetypes = mimetypes
        self.subject = subject
        self.html_body = html_body
        self.plaintext_body = plaintext_body
        self.entities = entities
        self.date = date
        self.ip_address = ip_address
        self.msg_id = msg_id
        self.thread_id = thread_id
        self.keywords = keywords

    def __str__(self) -> str:
        pp = pprint.PrettyPrinter(depth=4)
        output = f"Users in convo: {self.entities} \
            \nMessage Subject: {self.subject} \
            \nMessage parsed from html: {self.html_body} \
            \nMessage parsed from plaintext: {self.plaintext_body} \
            \nKeywords: {pp.pformat(self.keywords)}\n \
            \nMessage Date: {self.date} \
            \nMessage Labels: {self.labels} \
            \nProxy Mail IP address: {self.ip_address}\n\n"
        return output

class Builder(metaclass=ABCMeta):
    @abstractmethod
    def encryptText(self, content: str) -> str:
        pass

    @abstractmethod
    def generateCommObject(self, message: M) -> 'CommNodeBuilder':
        pass

    @abstractmethod
    def _parseHeaders(self, message: M) -> None:
        pass

    @abstractmethod
    def _parseDate(self,
                   timestamp: str,
                   *args,
                   **kwargs
                   ) -> None:
        pass

    @abstractmethod
    def _handleTrackedHeaders(self,
                              target: str,
                              *args,
                              **kwargs
                              ) -> Callable[[str], any]:
        pass

    @abstractmethod
    def _parseIP(self,
                 header: Dict[str, str],
                 *args,
                 **kwargs
                 ) -> None:
        pass

    @abstractmethod
    def _parseSubject(self,
                      header: Dict[str, str],
                      *args,
                      **kwargs
                      ) -> None:
        pass

    @abstractmethod
    def _parseEntities(self,
                       header: Dict[str, str],
                       msg_id: str,
                       *args,
                       **kwargs
                       ) -> None:
        pass

    @staticmethod
    @abstractmethod
    def createEntity(email: str,
                     name: str,
                     domain: str,
                     group: str,
                     poc: POC
                     ) -> Entity:
        pass

    @abstractmethod
    def _parseBody(self, message: M) -> None:
        pass

    @abstractmethod
    def _delegateToBodyParser(self,
                              target: str,
                              *args,
                              **kwargs
                              ) -> Callable[[str], str]:
        pass

    @abstractmethod
    def _parseHTMLBody(self, raw: bytes) -> None:
        pass

    @staticmethod
    @abstractmethod
    def mrClean() -> None:
        pass

    @abstractmethod
    def _parseTextBody(self, raw: bytes) -> None:
        pass

    @abstractmethod
    def _genKeywordCounter(self, text: str) -> Counter:
        pass

class CommNodeBuilder:
    '''
    Class containing the build logic for returning a new CommNode instance
    Methods:
    --------
        encryptText(self, content: str) -> str
            Takes a content string and encrypts the data for storage in Postgres

        generateCommObject(self, message: M) -> CommNodeBuilder
            Takes a raw message and parses the necessary information to store in Postgres.
            Returns an instance of itself to pass into the get_result function.

        _parseHeaders(self, message: M) -> None
            Creates a generator function to walk over the message
            headers and delegate them to specific parsers

        _handleTrackedHeaders(self, target, *args, **kwargs) -> Callable[[str], any]
            Delegates the target header to a specific parser
            and spreads *args, **kwargs into the parser

        _parseDate(self, timestamp: int, *args, **kwargs) -> None
            Parses the Unix MS Timestamp from internalDate field on
            Gmail Message response into a DateTime Object and updates instance attribute

        _parseIP(self, header: Dict[str, str], *args, **kwargs) -> None
            Parses IP addresses from Received-SPF header and updates instance attribute

        _parseSubject(self, header: Dict[str, str], *args, **kwargs) -> None
            Parses subject from Gmail API message header and updates instance attribute

        _parseEntities(self, header: Dict[str, str], msg_id: str, *args, **kwargs) -> None
            Parses the different entities in the message, creates
            Entity named tuples and stores them in the instance attribute container

        createEntity(email: str, name: str, domain: str, msg_id: str, poc: POC) -> Entity:
            Static method to create an Entity

        _parseBody(self, message: M) -> None:
            Generator function to walk the message parts and mimetypes and send to delegator

        _delegateToBodyParser(self, target: str, *args, **kwargs) -> Callable[[str], None]
            Handles delegation of parsing by mimetype

        _parseHTMLBody(self, raw: bytes) -> None
            Cleans and parses raw message body data with mimetype text/html

        mrClean() -> Generator[None, Union[str, Routine], str]:
            Generator function to streamline text cleaning pipelines
            and reduce memory / cpu consumption

        _parseTextBody(self, raw: bytes) -> None
            Cleans and parses raw message body data with mimetype text/plain

        _genKeywordCounter(self, text: str) -> Counter
            Tokenizes text, removes stopwords and punctuation,
            returns a counter object with the document vocabulary
    '''

    __slots__ = ['comm_obj', 'entities', 'mimetypes']

    def __init__(self) -> None:
        self.comm_obj = CommNode()
        self.entities = list()
        self.mimetypes = list()

    def encryptText(self, content: str) -> str:
        pass

    # @noArgClock
    # Need a way to take raw input from gmail api and return a cleaned comm node
    def generateCommObject(self, message: M) -> 'CommNodeBuilder':
        '''
        Top level function that takes a raw Message object from a Gmail
        API response and parses the necessary information into a suitable format
        for storing in Postgres for further analysis.

        Params:
        -------
            message: M
                a raw message response from a messages.get() request to Gmail API
        '''

        # Sets the date, ip_address, subject, and entity array variables
        self._parseHeaders(message)
        # Sets the comm_obj entity list to the builder entity list
        self.comm_obj.entities = self.entities
        # Parses date from internal date ms unix epoch timestamp
        self._parseDate(message.get('internalDate'))
        # Sets the html_body, plaintext_body, and mimetype array variables
        self._parseBody(message)
        # Sets the mimetype array on the comm_obj node
        self.comm_obj.mimetypes = self.mimetypes

        self.comm_obj.labels = message.get('labelIds', [])
        self.comm_obj.msg_id = message.get('id', '')
        self.comm_obj.thread_id = message.get('threadId', '')

        if len(self.comm_obj.plaintext_body) > 0:
            self.comm_obj.keywords = self._genKeywordCounter(self.comm_obj.plaintext_body)

        elif len(self.comm_obj.html_body) > 0:
            self.comm_obj.keywords = self._genKeywordCounter(self.comm_obj.html_body)


        return self

    # @noArgClock
    def _parseHeaders(self, message: M) -> None:
        # Generator to walk over the headers
        header_options = (header for header in message['payload']['headers']
                          if header['name'] in target_set)

        msg_id = message.get('id', None)

        while True:
            try:
                header = next(header_options)
            except StopIteration:
                break

            self._handleTrackedHeaders(header['name'], header, msg_id)

        return

    # @noArgClock
    def _handleTrackedHeaders(self,
                              target: str,
                              *args,
                              **kwargs
                              ) -> Callable[[str], any]:

        if target in poc_set:
            target = 'parse_entities'

        actions = {
            'Received-SPF': self._parseIP,
            'Subject': self._parseSubject,
            'parse_entities': self._parseEntities,
        }

        if target not in actions.keys():
            raise NotImplementedError(f'Header parser not implemented for {target}')

        return actions[target](*args, **kwargs)

    # @noArgClock
    def _parseDate(self, timestamp: int, *args, **kwargs) -> None:
        '''Instance method to set the message date as a datetime object'''
        cleaned_timestamp = int(timestamp) / 1000.0
        self.comm_obj.date = datetime.fromtimestamp(cleaned_timestamp)

    # @noArgClock
    def _parseIP(self, header: Dict[str, str], *args, **kwargs) -> None:
        '''
        Instance method to parse response headers from Gmail API and return an ip address string
        Params:
        -------
            header: Dict[str, str]
                Raw Received-SPF header
        '''

        target = header.get('value', '')
        self.comm_obj.ip_address = ', '.join(re.findall(r"\d+\.\d+\.\d+\.\d+", target))

        # ToDo: make a call to an external ip locator service asynchronously
        # ToDo: So that we can also store the location on each comm node

        return

    # @noArgClock
    def _parseSubject(self,
                      header: Dict[str, str],
                      *args,
                      **kwargs
                      ) -> None:
        '''
        Instance method to parse subject from Gmail API message header
        Params:
        -------
            header: Dict[str, str]
                Raw Subject header
        '''
        self.comm_obj.subject = header.get('value', '')
        return

    # @noArgClock
    def _parseEntities(self,
                       header: Dict[str, str],
                       msg_id: str,
                       *args,
                       **kwargs
                       ) -> None:
        '''
        Function to parse POC and entities for each POC

        Arguments:
        ----------
            poc_name: str
                To, From, Cc, Bcc
            poc_value: str
                eg: 'vinyl me, please <vinyl@gmail.com>, Qxhna Titcomb
                <qxhna.titcomb@techstars.com>, loop-zoop@gmail.com
            msg_id: str
                gmail api message id string
        '''

        # initialize empty list
        # entities = list(self.comm_obj.entities)

        # POC string is the 'Part Of Conversation' in uppercase
        # Used to create an instance of Enum for Entity
        poc_string = header.get('name', '').upper()
        poc_value = header.get('value', '')

        # set of all emails found by regex to help
        # with separating the names from the emails
        emails = set(re.findall(r"<?(\S*@[^>, ]*)", poc_value))

        # Generates all individual words from POC header value
        string_gen = (string for string in re.findall(r"[^<,> ]*", poc_value))

        entity_name = ''
        entity_email = ''

        while True:
            try:
                curr_string = next(string_gen)
            except StopIteration:
                break

            # if the current string is one of the emails, create an entity
            if curr_string in emails:
                poc = POC[poc_string]
                entity_email = curr_string.lower().replace('"', '')
                entity_domain = entity_email.split('@')[1]
                entity = self.createEntity(
                    entity_email,
                    entity_name.replace('"', ''),
                    entity_domain,
                    msg_id,
                    poc
                )

                # store it in the container
                self.entities.append(entity)

                # Reset name and email after appending to container
                entity_name = ''
                entity_email = ''

            # Otherwise, extend the entity name until an email is found
            else:
                entity_name += f' {curr_string}'

        return

    @staticmethod
    # @noArgClock
    def createEntity(email: str,
                     name: str,
                     domain: str,
                     msg_id: str,
                     poc: POC
                     ) -> Entity:

        return Entity(email, name, domain, msg_id, poc)

    # @noArgClock
    #   Chooses which text should be parsed and cleaned
    def _parseBody(self, message: M) -> None:
        '''
        Delegates raw message body to the appropriate parser to clean and store
        the message body text
        Params:
        -------
            message: M
                A message response from Gmail API

        '''

        # dict where keys are the mimetypes and the values are the raw messages
        mime_dict = {}


        # If the message is multi-part
        if 'multipart' in message.get('payload', {}).get('mimeType', ''):
            # Create a generator to iterate over the parts and delegate
            # the part's message to the appropriate parser
            parts = (part for part in message['payload']['parts'])

            while True:
                try:
                    curr = next(parts)
                except StopIteration:
                    break

                mimetype = curr.get('mimeType', '')
                raw_body = curr.get('body', {}).get('data', '')
                mime_dict[mimetype] = raw_body

        else:
            mimetype = message.get('payload', {}).get('mimeType', '')
            raw_body = message.get('payload', {}).get('body', {}).get('data', '')
            mime_dict[mimetype] = raw_body

        options = mime_dict.keys()
        self.mimetypes = [key for key in mime_dict.keys()]

        if 'text/plain' in options:
            self._delegateToBodyParser('text/plain', mime_dict['text/plain'])
            return

        elif 'text/html' in options:
            self._delegateToBodyParser('text/html', mime_dict['text/html'])
            return

        return

    # @noArgClock
    def _delegateToBodyParser(self,
                              target: str,
                              *args,
                              **kwargs
                              ) -> Callable[[str], None]:
        '''Delegates the raw message to a parser based off of its mimetype'''

        actions = {
            'text/html': self._parseHTMLBody,
            'text/plain': self._parseTextBody,
        }

        if target not in actions.keys():
            return

        return actions[target](*args, **kwargs)

    # @noArgClock
    def _parseHTMLBody(self, raw: bytes) -> None:
        '''
        Instance method to clean and parse raw message body data.

        Params:
        -------
            raw: bytes
                Raw base64 encoded message body with mimetype text/html
        '''

        decoded = base64.urlsafe_b64decode(raw)
        soup = BeautifulSoup(decoded, "lxml")
        body = soup.find('body')
        # Remove all html that isn't the target message
        quotes = body.find("div", {"class": "gmail_quote"})
        # Finds all style tags to remove them from the output
        styles = body.find_all('style')
        # Finds all script tags to remove them from the output
        scripts = body.find_all('script')

        if quotes is not None:
            quotes.decompose()

        for style in styles:
            style.decompose()

        for script in scripts:
            script.decompose()

        extracted = body.get_text(separator=' ', strip=True)
        self.comm_obj.html_body = extracted.lower()
        return

    @staticmethod
    def mrClean() -> Generator[None, Union[str, Routine], str]:
        ''' Generator function that handles text cleaning pipelines '''
        base_str = yield  # String to clean
        while True:
            op = yield  # text cleaning Routine
            if op is None:
                break
            try:
                base_str = re.sub(op.pattern, op.repl, base_str)
                # For debugging
                # print(f'Finished {op.op_name} \nOutput: {base_str} \n\n')
            except Exception as e:
                print(f'Error performing {op.op_name}: {e}')
                continue

        return base_str.lower()


    def _parseTextBody(self, raw: bytes) -> None:
        '''
        Instance method to clean and parse raw message body data.

        Params:
        -------
            raw: bytes
                Raw base64 encoded message body with mimetype text/plain
        '''

        routines = [
            Routine(r"\r", '', 'removing returns'),
            Routine(r"\n", ' ', 'removing newlines'),
            Routine(r"On\s\w{3},?\s.*?<\s?\S*?@\S*?\s?>.*", '', 'removing email quotes'),
            Routine(r"<.*?\/>|<.*?><\/.*?>", '', 'removing HTML elements'),
            Routine(r"http?s?://\S+", '', 'removing urls'),
            Routine(r"\w*?=\"\S+|\S*?:\s?\S*?;\"?", '', 'removing css styles'),
            Routine(r" {1,}", ' ', 'removing extra spaces'),
            Routine(r"<\S*?>", '', 'removing HTML tags'),
            None
        ]

        decoded = base64.urlsafe_b64decode(raw).decode('utf-8')
        cleaned = ''

        text_cleaner = self.mrClean()
        next(text_cleaner)  # Prime the Generator
        text_cleaner.send(decoded)  # Send the text that needs cleaning

        for routine in routines:
            try:
                text_cleaner.send(routine)
            except StopIteration as exc:
                cleaned = exc.value

        clean_words = ' '.join(re.findall(r"[a-zA-Z']{2,}", cleaned))
        self.comm_obj.plaintext_body = clean_words
        return

    # @noArgClock
    def _genKeywordCounter(self, text: str) -> Counter:
        ''' Creates a Spacy NLP object with the cleaned message body text,
        tokenizes the data, removes stopwords and punctuation,
        then returns a Counter object containing word occurrences.

        Params:
        -------
            text: str
                Input string to clean and count keywords from
        '''
        spacy_doc = nlp(text)

        token_list = (token for token in spacy_doc)
        filtered = []

        while True:
            try:
                curr = next(token_list)
            except StopIteration:
                break

            if curr.is_stop is False and curr.is_punct is False:
                filtered.append(curr.text)

        return Counter(filtered)

    # @noArgClock
    def get_result(self) -> CommNode:
        return self.comm_obj


class CommNodeBuildManager:
    '''
    Handles building and returning a new CommNode object

    Methods:
    --------
        construct(message: M)
            Takes a message response from Gmail api and returns a new instance
            of CommNode data class
    '''

    @staticmethod
    def construct(message: M) -> CommNode:
        return CommNodeBuilder().generateCommObject(
            message
        ).get_result()
