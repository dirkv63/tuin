"""
This module consolidates all local configuration for the script, including modulename collection for logfile name
setup and initializing the config file.
Also other utilities find their home here.
"""

# import datetime
import logging
import logging.handlers
import os
import platform
import re
import sys
import time
from calendar import timegm
from datetime import datetime


def init_env(projectname, filename):
    """
    This function will initialize the environment: Find and return handle to config.py file and set-up logging.
    
    :param projectname: Name that will be used to find ini file in properties subdirectory.
    :param filename: Filename (__file__) of the calling script (for logfile).
    :return: config.py handle
    """
    projectname = projectname
    modulename = get_modulename(filename)
    config = get_inifile(projectname)
    my_log = init_loghandler(modulename, config["Main"]["logdir"], config["Main"]["loglevel"])
    my_log.info('Start Application')
    return config


def get_inifile(projectname):
    """
    Read Project configuration ini file in subdirectory properties. Config ini filename is the projectname.
    The ini file is located in the properties module, which is sibling of the lib module.
    :param projectname: Name of the project.
    :return: Object reference to the inifile.
    """
    # Use Project Name as ini file.
    # TODO: review procedure to get directory name instead of relative properties/ path.
    if getattr(sys, 'frozen', False):
        # Running Frozen (pyinstaller executable)
        configfile = projectname + ".ini"
    else:
        # Running Live
        # properties directory is sibling of lib directory.
        (filepath_lib, _) = os.path.split(__file__)
        (filepath, _) = os.path.split(filepath_lib)
        # configfile = filepath + "/properties/" + projectname + ".ini"
        configfile = os.path.join(filepath, 'properties', "{p}.ini".format(p=projectname))
    ini_config = configparser.ConfigParser()
    try:
        f = open(configfile)
        ini_config.read_file(f)
        f.close()
    except FileNotFoundError:
        e = sys.exc_info()[1]
        ec = sys.exc_info()[0]
        log_msg = "Read Inifile not successful: %s (%s)"
        print(log_msg % (e, ec))
        sys.exit(1)
    return ini_config


def get_modulename(scriptname):
    """
    Modulename is required for logfile and sometimes for properties file. Module name is the filename, without extension
    and without directory path.

    :param scriptname: Name of the script for which modulename is required. Use __file__ in the calling application.
    :return: Module Filename from the calling script.
    """
    # Extract calling application name
    (filepath, filename) = os.path.split(scriptname)
    (modulename, _) = os.path.splitext(filename)
    return modulename


def init_loghandler(scriptname, logdir, loglevel):
    """
    This function initializes the loghandler. Logfilename consists of calling module name + computername.
    Logfile directory is read from the project .ini file.
    Format of the logmessage is specified in basicConfig function.
    This is for Log Handler configuration. If basic log file configuration is required, then use init_logfile.
    Review logger, there seems to be a conflict with the flask logger.
    :param scriptname: Name of the calling module.
    :param logdir: Directory of the logfile.
    :param loglevel: The loglevel for logging.
    :return: logging handler
    """
    modulename = get_modulename(scriptname)
    loglevel = loglevel.upper()
    # Extract Computername
    computername = platform.node()
    # Define logfileName
    logfile = logdir + "/" + modulename + "_" + computername + ".log"
    # Set loglevel for bolt driver to warning
    logging.getLogger("neo4j.bolt").setLevel(logging.WARNING)
    # logging.getLogger("neo4j.http").setLevel(logging.WARNING)
    logging.getLogger("httpstream").setLevel(logging.WARNING)
    # Configure the root logger
    logger = logging.getLogger()
    level = logging.getLevelName(loglevel)
    logger.setLevel(level)
    # Create Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    # Create Rotating File Handler
    # Get logfiles of 1M
    maxbytes = 1024 * 1024
    rfh = logging.handlers.RotatingFileHandler(logfile, maxBytes=maxbytes, backupCount=5)
    # Create Formatter for file
    formatter_file = logging.Formatter(fmt='%(asctime)s|%(module)s|%(funcName)s|%(lineno)d|%(levelname)s|%(message)s',
                                       datefmt='%d/%m/%Y|%H:%M:%S')
    formatter_console = logging.Formatter(fmt='%(asctime)s - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s -'
                                              ' %(message)s',
                                          datefmt='%H:%M:%S')
    # Add Formatter to Console Handler
    ch.setFormatter(formatter_console)
    # Add Formatter to Rotating File Handler
    rfh.setFormatter(formatter_file)
    # Add Handler to the logger
    # logger.addHandler(ch)
    logger.addHandler(rfh)
    return logger


def date2epoch(ds):
    """
    This function will convert a date time string to epoch for storage in SQLite table.

    :param ds: Date time string in format %Y-%m-%d %H:%M:%S

    :return: epoch - seconds since 1/01/1970
    """
    utc_time = time.strptime(ds, "%Y-%m-%d %H:%M:%S")
    return timegm(utc_time)


def reformat_body(string, is_xhtml=True):
    """
    This function will wrap http with href for redirecting.
    This function will replace \n with <br />.
    However don't do this around valid html identifiers.
    From Drupal - additional info on http://www.php2python.com/wiki/function.reformat_body/
    This is used as a Jinja2 filter.

    :param string:

    :param is_xhtml:

    :return:
    """
    # First wrap URLs in href.
    # Only wrap URLs if there is no href in the body text
    string = altfix_urls(string)
    # Then replace \n with <br>
    # TODO: add a function that collects strings from within the html DOM domain, so that \n surrounding htlm (as in
    # TODO: <table> is not touched.
    if is_xhtml:
        return string.replace('\n', '<br />\n')
    else:
        return string.replace('\n', '<br>\n')


def children_sorted(children):
    return sorted(children, key=lambda child: child.content.title)


def nodes_sorted(nodes):
    return sorted(nodes, key=lambda node: node.created, reverse=True)[:10]


def terms_sorted(terms):
    return sorted(terms, key=lambda term: (term.vocabularies.name, term.name))


URL_REGEX = re.compile(r'''((?:mailto:|ftp://|http://|https://)[^ <>'"{}|\\^`[\]]*)''')


def altfix_urls(text):
    if not ('href' in text.lower()):
        return URL_REGEX.sub(r'<a target="_blank" href="\1">\1</a>', text)
    else:
        return text


def fix_urls(text):
    """
    Additional info on https://stackoverflow.com/questions/1071191/detect-urls-in-a-string-and-wrap-with-a-href-tag

    Not that this does not work if the URL has a href already. These pages may need to be removed.

    :param text:

    :return:
    """
    pat_url = re.compile(r'''
                     (?x)( # verbose identify URLs within text
   (http|https|ftp|gopher) # make sure we find a resource type
                       :// # ...needs to be followed by colon-slash-slash
            (\w+[:.]?){2,} # at least two domain groups, e.g. (gnosis.)(cx)
                      (/?| # could be just the domain name (maybe w/ slash)
                [^ \n\r"]+ # or stuff then space, newline, tab, quote
                    [\w/]) # resource name ends in alphanumeric or slash
         (?=[\s.,>)'"\]]) # assert: followed by white or clause ending
                         ) # end of match group
                           ''')
    pat_email = re.compile(r'''
                    (?xm)  # verbose identify URLs in text (and multiline)
                 (?=^.{11} # Mail header matcher
         (?<!Message-ID:|  # rule out Message-ID's as best possible
             In-Reply-To)) # ...and also In-Reply-To
                    (.*?)( # must grab to email to allow prior lookbehind
        ([A-Za-z0-9-]+\.)? # maybe an initial part: DAVID.mertz@gnosis.cx
             [A-Za-z0-9-]+ # definitely some local user: MERTZ@gnosis.cx
                         @ # ...needs an at sign in the middle
              (\w+\.?){2,} # at least two domain groups, e.g. (gnosis.)(cx)
         (?=[\s\.,>)'"\]]) # assert: followed by white or clause ending
                         ) # end of match group
                           ''')

    for url in re.findall(pat_url, text):
        text = text.replace(url[0], '<a href="%(url)s">%(url)s</a>' % {"url": url[0]})

    for email in re.findall(pat_email, text):
        text = text.replace(email[1], '<a href="mailto:%(email)s">%(email)s</a>' % {"email": email[1]})

    return text


def datestamp(epoch):
    """
    This is a Jinja2 filter

    :param epoch: Unix timestamp - seconds since 1/01/1970 UTC

    :return: Date in format 'DD/MM/YY HH:MM
    """
    return datetime.fromtimestamp(epoch).strftime('%d/%m/%y')


def monthdisp(ym):
    """
    This is a Jinja2 filter to convert %Y-%m into month Year.

    :param ym: Date in %Y-%m format

    :return: Date in month Year format.
    """
    month_arr = ["januari", "februari", "maart", "april", "mei", "juni",
                 "juli", "augustus", "september", "oktober", "november", "december"]
    (yr, mnth) = ym.split("-")
    return "{m} {y}".format(y=yr, m=month_arr[int(mnth)-1])


class LoopInfo:
    """
    This class handles a FOR loop information handling.
    """

    def __init__(self, attribname, triggercnt):
        """
        Initialization of FOR loop information handling. Start message is printed for attribname. Information progress
        message will be printed for every triggercnt iterations.
        :param attribname:
        :param triggercnt:
        :return:
        """
        self.rec_cnt = 0
        self.loop_cnt = 0
        self.attribname = attribname
        self.triggercnt = triggercnt
        curr_time = datetime.now().strftime("%H:%M:%S")
        print("{0} - Start working on {1}".format(curr_time, str(self.attribname)))
        return

    def info_loop(self):
        """
        Check number of iterations. Print message if number of iterations greater or equal than triggercnt.
        :return:
        """
        self.rec_cnt += 1
        self.loop_cnt += 1
        if self.loop_cnt >= self.triggercnt:
            curr_time = datetime.now().strftime("%H:%M:%S")
            print("{0} - {1} {2} handled".format(curr_time, str(self.rec_cnt), str(self.attribname)))
            self.loop_cnt = 0
        return

    def end_loop(self):
        curr_time = datetime.now().strftime("%H:%M:%S")
        print("{0} - {1} {2} handled - End.\n".format(curr_time, str(self.rec_cnt), str(self.attribname)))
        return
