import csv
import re
import string
import uuid

from collections import namedtuple
from datetime import datetime
from faker import Faker
from random import uniform, randint, choice
from time import mktime
from .time_parser import time_parse
import os

from . import SampleEvent
import logging
import warnings

LOGGER = logging.getLogger("pytest-splunk-addon")

user_email_count = 0
# user_email_count to generate unique values for
# ["name", "email", "domain_user", "distinquised_name"] in each token

event_host_count = 0
# event_host_count is used to generate unique host for each event in
# case of replacementType = all


class Rule:
    """
    Base class for all the rules.
    """
    user_header = ["name", "email", "domain_user", "distinquised_name"]
    src_header = ["host", "ipv4", "ipv6", "fqdn"]
    token_value = namedtuple("token_value", ['key', 'value'])

    def __init__(self, token, eventgen_params=None, sample_path=None):
        self.token = token["token"]
        self.replacement = token["replacement"]
        self.replacement_type = token["replacementType"]
        self.field = token.get("field", self.token.strip("#"))
        self.eventgen_params = eventgen_params
        self.sample_path = sample_path
        self.fake = Faker()

    @classmethod
    def parse_rule(cls, token, eventgen_params, sample_path):
        """
        Returns appropriate Rule class object as per replacement type of token.

        Args:
            token(dict): represents a single token object.
            eventgen_params(dict): Dict object of the common params
            for each stanza.
            sample_path(str): Path to the samples directory.
        """
        rule_book = {
            "integer": IntRule,
            "list": ListRule,
            "ipv4": Ipv4Rule,
            "float": FloatRule,
            "ipv6": Ipv6Rule,
            "mac": MacRule,
            "file": FileRule,
            "url": UrlRule,
            "user": UserRule,
            "email": EmailRule,
            "host": HostRule,
            "hex": HexRule,
            "src_port": SrcPortRule,
            "dest_port": DestPortRule,
            "src": SrcRule,
            "dest": DestRule,
            "dvc": DvcRule,
            "guid": GuidRule
        }

        replacement_type = token["replacementType"]
        replacement = token["replacement"]
        if replacement_type == "static":
            return StaticRule(token)
        elif replacement_type == "timestamp":
            return TimeRule(token, eventgen_params)
        elif replacement_type == "random" or replacement_type == "all":
            for each_rule in rule_book:
                if replacement.lower().startswith(each_rule):
                    return rule_book[each_rule](token, sample_path=sample_path)
        elif replacement_type == "file" or replacement_type == "mvfile":
            return FileRule(token, sample_path=sample_path)

        LOGGER.error(
            f"No Rule Found for token = {token.get('token')},"
            f"with replacement = {replacement}"
            f"and replacement_type = {replacement_type}!"
        )
        warnings.warn(UserWarning(
                    f"No Rule Found for token = {token.get('token')},"
                    f"with replacement = {replacement}"
                    f"and replacement_type = {replacement_type}!"
                    ))

    def apply(self, events):
        """
        Replaces the token with appropriate values as per rules mapped
        with the token for the event.
        For replacement_type = all it will generate an event
        for each replacement value.
        i.e. integer[1:50] => will generate 50 events

        Args:
            events(list): List of event(SampleEvent)
        """
        new_events = []
        for each_event in events:
            token_count = each_event.get_token_count(self.token)
            token_values = list(self.replace(each_event, token_count))
            if self.replacement_type == "all" and token_count > 0:
                # NOTE: If replacement_type is all and same token is more than
                #       one time in event then replace all tokens with same
                #       value in that event
                for each_token_value in token_values:
                    new_event = SampleEvent.copy(each_event)
                    global event_host_count
                    event_host_count += 1
                    new_event.metadata["host"] = "{}_{}".format(
                        each_event.sample_name, event_host_count
                        )
                    new_event.replace_token(self.token, each_token_value.value)
                    new_event.register_field_value(
                        self.field, each_token_value.key
                    )
                    new_events.append(new_event)
            else:
                each_event.replace_token(
                    self.token,
                    token_values
                )
                each_event.register_field_value(self.field, token_values)
                new_events.append(each_event)
        return new_events

    def get_lookup_value(self, sample, key, headers, value_list):
        """
        Common method to read csv and get a random row.

        Args:
            sample(object): Instance of SampleEvent class.
            key(str): fieldname i.e. host, src, user, dvc etc
            headers(list): Headers of csv file in list format.
            value_list(list): list of replacement values
            mentioned in configuration file.

        Returns:
            index_list(list): list of mapped columns(int) as per value_list
            csv_row(list): list of replacement values for the rule.
        """
        csv_row = []
        global user_email_count
        user_email_count += 1
        name = "user{}".format(user_email_count)
        email = "user{}@email.com".format(user_email_count)
        domain_user = r"sample_domain.com\user{}".format(user_email_count)
        distinguished_name = "CN=user{}".format(user_email_count)
        csv_row.extend([name, email, domain_user, distinguished_name])
        index_list = [
            i
            for i, item in enumerate(headers)
            if item in value_list
        ]
        if (
            hasattr(sample, "replacement_map")
            and key in sample.replacement_map
        ):
            sample.replacement_map[key].append(csv_row)
        else:
            sample.__setattr__("replacement_map", {key: [csv_row]})
        return index_list, csv_row

    def get_rule_replacement_values(self, sample, value_list, rule):
        """
        Common method for replacement values of
        SrcRule, Destrule, DvcRule, HostRule.

        Args:
            sample(object): Instance of SampleEvent class.
            value_list(list): list of replacement values
            mentioned in configuration file.
            rule(str): fieldname i.e. host, src, user, dvc etc

        Returns:
            index_list(list): list of mapped columns(int) as per value_list
            csv_row(list): list of replacement values for the rule.
        """
        csv_row = []
        for each in value_list:
            if each == "host":
                csv_row.append(sample.get_field_host(rule))
            elif each == "ipv4":
                csv_row.append(sample.get_ipv4(rule))
            elif each == "ipv6":
                csv_row.append(sample.get_ipv6(rule))
            elif each == "fqdn":
                csv_row.append(sample.get_field_fqdn(rule))
        return csv_row


class IntRule(Rule):
    """
    IntRule 
    """
    def replace(self, sample, token_count):
        """
        Yields a random int between the range mentioned in token.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        lower_limit, upper_limit = re.match(
            r"[Ii]nteger\[(\d+):(\d+)\]", self.replacement
        ).groups()
        if self.replacement_type == "random":
            for _ in range(token_count):
                yield self.token_value(
                    *([randint(int(lower_limit), int(upper_limit))]*2)
                    )
        else:
            for each_int in range(int(lower_limit), int(upper_limit)):
                yield self.token_value(
                    *([str(each_int)]*2)
                    )


class FloatRule(Rule):
    """
    FloatRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random float no. between the range mentioned in token.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        lower_limit, upper_limit = re.match(
            r"[Ff]loat\[([\d\.]+):([\d\.]+)\]", self.replacement
        ).groups()
        precision = re.search("\[\d+\.?(\d*):", self.replacement).group(1)
        if not precision:
            precision = str(1)
        for _ in range(token_count):
            yield self.token_value(
                    *([round(
                        uniform(
                            float(lower_limit),
                            float(upper_limit)
                            ),
                        len(precision),
                        )
                      ]*2)
                    ) 


class ListRule(Rule):
    """
    ListRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random value from the list mentioned in token.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        value_list_str = re.match(
            r"[lL]ist(\[.*?\])", self.replacement
        ).group(1)
        value_list = eval(value_list_str)

        if self.replacement_type == "random":
            for _ in range(token_count):
                yield self.token_value(*([str(choice(value_list))]*2))
        else:
            for each_value in value_list:
                yield self.token_value(*([str(each_value)]*2))


class StaticRule(Rule):
    """
    StaticRule
    """
    def replace(self, sample, token_count):
        """
        Yields the static value mentioned in token.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event where rule
            is to be applicable.
        """
        for _ in range(token_count):
            yield self.token_value(*([self.replacement]*2))


class FileRule(Rule):
    """
    FileRule
    """
    def replace(self, sample, token_count):
        """
        Yields the values of token by reading files.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event where rule
            is to be applicable.
        """
        if self.replacement.startswith("file" or "File"):
            sample_file_path = re.match(
                    r"[fF]ile\[(.*?)\]", self.replacement
                ).group(1)
        else:
            sample_file_path = self.replacement

        sample_file_path = sample_file_path.replace("/", os.sep)

        relative_file_path = self.sample_path.split(f"{os.sep}samples")[0]
        try:
            # get the relative_file_path and index value from filepath
            # mentioned in the token if the filepath matches the pattern
            # pattern like: <directory_path>/apps/<addon_name>/<file_path> or
            # pattern like:
            # <directory_path>/apps/<addon_name>/<file_path>:<index>
            _, splitter, file_path = re.search(
                r"(.*)(\\?\/?apps\\?\/?[a-zA-Z-_0-9.*]+\\?\/?)(.*)",
                sample_file_path
                ).groups()
            relative_file_path = os.path.join(
                relative_file_path,
                file_path.split(":")[0]
                )
            file_index = file_path.split(":")
            index = (file_index[1] if len(file_index) > 1 else None)

            if not os.path.isfile(relative_file_path):
                raise AttributeError

        except AttributeError:
            # get the relative_file_path and index value from filepath
            # mentioned in the token if the filepath matches the pattern
            # pattern like: <directory_path>/<file_path> or
            # pattern like: <directory_path>/<file_path>:<index>
            file_path = sample_file_path
            index = None
            if file_path.count(":") > 0:
                file_index = file_path.rsplit(":", 1)
                index = (file_index[1] if len(file_index) > 1 else None)
                file_path = file_path.rsplit(":", 1)[0]
            relative_file_path = file_path

        if self.replacement_type in ['random', 'file']:
            # yield random value for the token by reading sample file
            try:
                if index:
                    try:
                        index = int(index)
                        for i in self.indexed_sample_file(
                                relative_file_path,
                                index,
                                token_count):
                            yield self.token_value(i, i)

                    except ValueError:
                        for i in self.lookupfile(
                                relative_file_path,
                                index,
                                token_count):
                            yield self.token_value(i,i)
                else:
                    with open(relative_file_path) as f:
                        txt = f.read()
                        lines = [each for each in txt.split("\n") if each]
                        for _ in range(token_count):
                            yield self.token_value(
                                *([choice(lines)]*2)
                                )
            except IOError:
                LOGGER.warning(
                    "File not found : {}".format(relative_file_path)
                    )

        elif self.replacement_type == 'all':
            # yield all values present in sample file for
            # the token by reading sample file
            # it will not generate the value for indexed files
            if index:
                LOGGER.error((
                    "replacement_type 'all' is not supported",
                    "for indexed file '{}'".format(
                        os.path.basename(file_path)
                        )
                    ))
                yield self.token_value(*([self.token]*2))
            else:
                with open(relative_file_path) as f:
                    txt = f.read()
                    for each_value in txt.split("\n"):
                        yield self.token_value(*([each_value]*2))

    def indexed_sample_file(self, file_path, index, token_count):
        """
        Yields the column value of token by reading files.

        Args:
            file_path: path of the file mentioned in token.
            index: index value mentioned in file_path i.e. <file_path>:<index>
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        try:
            with open(file_path, 'r') as f:
                output = []
                for line in f:
                    cells = line.split(",")
                    output.append((cells[index-1].strip("\n")))
                for _ in range(token_count):
                    yield choice(output)
        except IndexError:
            LOGGER.error(
                f"Index for column {index} in replacement"
                f"file {file_path} is out of bounds"
                )
        except IOError:
            raise IOError

    def lookupfile(self, file_path, index, token_count):
        """
        Yields the column value of token by reading files.

        Args:
            file_path: path of the file mentioned in token.
            index: index value mentioned in file_path i.e. <file_path>:<index>
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        try:
            with open(file_path, 'r') as f:
                output = []
                data = csv.DictReader(f)
                try:
                    for row in data:
                        for col in [index]:
                            output.append(row[col])
                    for _ in range(token_count):
                        yield choice(output)
                except KeyError:
                    LOGGER.error(
                        f"Column {index} is not present"
                        "replacement file {file_path}"
                        )
        except IOError:
            raise IOError


class TimeRule(Rule):

    def replace(self, sample, token_count):
        """
        Args :
            sample_raw - sample event to be updated as per replacement
            for token.
            earliest - splunktime formated time.
            latest - splunktime formated time.
            timezone - time zone according to which time is to be generated

        returns :
            random time according to the parameters specified in the input.
        """
        earliest = self.eventgen_params.get("earliest")
        latest = self.eventgen_params.get("latest")
        timezone = self.eventgen_params.get("timezone")
        random_time = datetime.now()
        time_parser = time_parse()

        if earliest != "now" and earliest is not None:
            sign, num, unit = re.match(
                r"([+-])(\d{1,})(.*)", earliest
            ).groups()
            earliest = time_parser.convert_to_time(sign, num, unit)
        else:
            earliest = datetime.now()

        if latest != "now" and latest is not None:
            sign, num, unit = re.match(r"([+-])(\d{1,})(.*)", latest).groups()
            latest = time_parser.convert_to_time(sign, num, unit)
        else:
            latest = datetime.now()

        earliest_in_epoch = mktime(earliest.timetuple())
        latest_in_epoch = mktime(latest.timetuple())

        if earliest_in_epoch > latest_in_epoch:
            LOGGER.info("Latest time is earlier than earliest time.")
            yield self.token
        for _ in range(token_count):
            random_time = datetime.fromtimestamp(
                randint(earliest_in_epoch, latest_in_epoch)
            )
            if timezone != "'local'" and timezone is not None:
                sign, hrs, mins = re.match(
                    r"([+-])(\d\d)(\d\d)", timezone
                ).groups()
                random_time = time_parser.get_timezone_time(
                    random_time, sign, hrs, mins
                )

            if r"%s" == self.replacement.strip("'").strip('"'):
                yield self.token_value(
                    *([self.replacement.replace(
                        r"%s", str(int(mktime(random_time.timetuple())))
                        )]*2)
                    )

            yield self.token_value(
                int(mktime(random_time.timetuple())),
                random_time.strftime(
                    random_time.strftime(
                        self.replacement.replace(r'%e', r'%d')
                        )
                    )
                )


class Ipv4Rule(Rule):
    """
    Ipv4Rule
    """
    def replace(self, sample, token_count):
        """
        Yields a random ipv4 address.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        for _ in range(token_count):
            yield self.token_value(*([self.fake.ipv4()]*2))


class Ipv6Rule(Rule):
    """
    Ipv6Rule
    """
    def replace(self, sample, token_count):
        """
        Yields a random ipv6 address

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        for _ in range(token_count):
            yield self.token_value(*([self.fake.ipv6()]*2))


class MacRule(Rule):
    """
    MacRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random mac address

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        for _ in range(token_count):
            yield self.token_value(*([self.fake.mac_address()]*2))


class GuidRule(Rule):
    """
    GuidRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random guid.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        for _ in range(token_count):
            yield self.token_value(*([str(uuid.uuid4())]*2))


class UserRule(Rule):
    """
    UserRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random user replacement value from the list
        of values mentioned in token.
        Possible values: ["name","email","domain_user","distinquised_name"]

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        value_list_str = re.match(
            r"[uU]ser(\[.*?\])", self.replacement
        ).group(1)
        value_list = eval(value_list_str)

        for i in range(token_count):
            if (
                hasattr(sample, "replacement_map")
                and "email" in sample.replacement_map
                and i < len(sample.replacement_map["email"])
            ):
                index_list = [
                    i
                    for i, item in enumerate(self.user_header)
                    if item in value_list
                ]
                csv_rows = sample.replacement_map["email"]
                yield self.token_value(
                    *([csv_rows[i][choice(index_list)]]*2)
                    )
            else:
                index_list, csv_row = self.get_lookup_value(
                    sample,
                    "user",
                    self.user_header,
                    value_list,
                )
                yield self.token_value(*([csv_row[choice(index_list)]]*2))


class EmailRule(Rule):
    """
    EmailRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random email from the lookups\\user_email.csv.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """

        for i in range(token_count):
            if (
                hasattr(sample, "replacement_map")
                and "user" in sample.replacement_map
                and i < len(sample.replacement_map["user"])
            ):
                csv_rows = sample.replacement_map["user"]
                yield self.token_value(
                    *([csv_rows[i][self.user_header.index("email")]]*2)
                    )
            else:
                index_list, csv_row = self.get_lookup_value(
                    sample,
                    "email",
                    self.user_header,
                    ["email"],
                )
                yield self.token_value(
                    *([csv_row[choice(index_list)]]*2)
                    )


class UrlRule(Rule):
    """
    UrlRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random url replacement value from the list
        of values mentioned in token.
        Possible values: ["ip_host", "fqdn_host", "path", "query", "protocol"]

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        value_list_str = re.match(r"[uU]rl(\[.*?\])", self.replacement).group(
            1
        )
        value_list = eval(value_list_str)

        for _ in range(token_count):
            if bool(
                set(["ip_host", "fqdn_host", "full"]).intersection(value_list)
            ):
                url = ""
                domain_name = []
                if bool(set(["full", "protocol"]).intersection(value_list)):
                    url = url + choice(["http://", "https://"])
                if bool(set(["full", "ip_host"]).intersection(value_list)):
                    domain_name.append(self.fake.ipv4())
                if bool(set(["full", "fqdn_host"]).intersection(value_list)):
                    domain_name.append(self.fake.hostname())
                url = url + choice(domain_name)
            else:
                url = self.fake.url()

            if bool(set(["full", "path"]).intersection(value_list)):
                url = (
                    url
                    + "/"
                    + choice(
                        [
                            self.fake.uri_path(),
                            self.fake.uri_page() + self.fake.uri_extension(),
                        ]
                    )
                )

            if bool(set(["full", "query"]).intersection(value_list)):
                url = url + self.generate_url_query_params()
            yield self.token_value(*([str(url)]*2))

    def generate_url_query_params(self):
        """
        This method is generate the random query params for url
        Returns:
            Return the query param string
        """
        url_params = "?"
        for _ in range(randint(1, 4)):
            field = "".join(
                choice(string.ascii_lowercase) for _ in range(randint(2, 5))
            )
            value = "".join(
                choice(string.ascii_lowercase + string.digits)
                for _ in range(randint(2, 5))
            )
            url_params = url_params + field + "=" + value + "&"
        return url_params[:-1]


class DestRule(Rule):
    """
    DestRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random dest replacement value from the list
        of values mentioned in token.
        Possible values: ["host", "ipv4", "ipv6", "fqdn"]

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        value_list_str = re.match(
            r"[dD]est(\[.*?\])", self.replacement
        ).group(1)

        value_list = eval(value_list_str)

        for _ in range(token_count):
            csv_row = self.get_rule_replacement_values(
                sample,
                value_list,
                rule="dest"
            )
            yield self.token_value(
                *([choice(csv_row)]*2)
                )


class SrcPortRule(Rule):
    """
    SrcPortRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random port value from the range 4000-5000

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        for _ in range(token_count):
            yield self.token_value(
                *([randint(4000, 5000)]*2)
                )


class DvcRule(Rule):
    """
    DvcRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random dvc replacement value from the list
        of values mentioned in token.
        Possible values: ["host", "ipv4", "ipv6", "fqdn"]

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        value_list_str = re.match(r"[dD]vc(\[.*?\])", self.replacement).group(
            1
        )
        value_list = eval(value_list_str)
        for _ in range(token_count):
            csv_row = self.get_rule_replacement_values(
                sample,
                value_list,
                rule="dvc"
                )
            yield self.token_value(*([choice(csv_row)]*2))


class SrcRule(Rule):
    """
    SrcRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random src replacement value from the list
        of values mentioned in token.
        Possible values: ["host", "ipv4", "ipv6", "fqdn"]

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        value_list_str = re.match(r"[sS]rc(\[.*?\])", self.replacement).group(
            1
        )
        value_list = eval(value_list_str)
        for _ in range(token_count):
            csv_row = self.get_rule_replacement_values(
                sample,
                value_list,
                rule="src"
                )
            yield self.token_value(*([choice(csv_row)]*2))


class DestPortRule(Rule):
    """
    DestPortRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random port value from [80, 443, 25, 22, 21]

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        DEST_PORT = [80, 443, 25, 22, 21]
        for _ in range(token_count):
            yield self.token_value(*([choice(DEST_PORT)]*2))


class HostRule(Rule):
    """
    HostRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random host replacement value from the list
        of values mentioned in token.
        Possible values: ["host", "ipv4", "ipv6", "fqdn"]

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        value_list_str = re.match(
            r"[hH]ost(\[.*?\])", self.replacement
        ).group(1)
        value_list = eval(value_list_str)
        for _ in range(token_count):
            csv_row = self.get_rule_replacement_values(
                sample, value_list, rule="host"
            )
            if "host" in value_list:
                if sample.metadata.get("input_type") in [
                    "modinput",
                    "windows_input",
                ]:
                    host_value = sample.metadata.get("host")
                elif sample.metadata.get("input_type") in [
                    "file_monitor",
                    "scripted_input",
                    "syslog_tcp",
                    "syslog_udp",
                    "other",
                ]:
                    host_value = sample.get_host()
                csv_row[0] = host_value
            yield self.token_value(*([choice(csv_row)]*2))


class HexRule(Rule):
    """
    HexRule
    """
    def replace(self, sample, token_count):
        """
        Yields a random hex value.

        Args:
            sample(object): Instance of SampleEvent class.
            token_count(int): No. of token in sample event
            where rule is to be applicable.
        """
        hex_range = re.match(r"[Hh]ex\((.*?)\)", self.replacement).group(1)
        hex_digits = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
        ]
        hex_array = []
        for _ in range(token_count):
            for i in range(int(hex_range)):
                hex_array.append(hex_digits[randint(0, 15)])
            hex_value = "".join(hex_array)
            yield self.token_value(*([hex_value]*2))
