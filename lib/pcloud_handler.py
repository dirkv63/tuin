import logging
import requests


class PcloudHandler:

    """
    This class consolidates the pcloud functionality. On initialization a connection to pcloud account is set.
    List method allows to list all files in the specified folder. Logout method will close the connection.
    """

    def __init__(self, config_hdl):
        """
        On initialization a connection to pcloud account is done.

        :param config_hdl:
        """
        user = config_hdl["Pcloud"]["user"]
        passwd = config_hdl["Pcloud"]["passwd"]
        params = dict(username=user, password=passwd, getauth=1)
        self.url_base = config_hdl["Pcloud"]["home"]
        method = "userinfo"
        url = self.url_base + method
        self.session = requests.Session()
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not connect to pcloud. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            logging.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        self.auth = res["auth"]
        usedquota = res["usedquota"]
        quota = res["quota"]
        pct = (usedquota/quota)*100
        msg = "{pct:.2f}% used.".format(pct=pct)
        logging.info(msg)

    def get_contents(self, path="/", recursive=False):
        """
        This method will return the contents of directory on path.

        :param path: Top path for which directory contents need to be returned. (default="/")
        :param recursive: True/False - recursive directory walk (default: False).
        :return: Content of the pcloud directory for the user.
        """
        if recursive:
            recursive=1
        else:
            recursive=0
        params = dict(path=path, recursive=recursive)
        method = "listfolder"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not connect to pcloud. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            logging.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res["metadata"]

    def copyfile(self, fileid, tofolderid):
        """
        This method copies a file to a destination folder.

        :param fileid: ID of the file to be copied.
        :param tofolderid: Target folder.
        :return:
        """
        params = dict(fileid=fileid, tofolderid=tofolderid)
        method = "copyfile"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not copy file. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            logging.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res

    def listfolder(self, folderid):
        """
        This method will get a folder ID and return json string with folder information.

        :param folderid: ID of the folder for which the info is required
        :return:
        """
        # Todo: merge method with get_contents method.
        params = dict(folderid=folderid)
        method = "listfolder"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not collect metadata. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            logging.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res

    def logout(self):
        method = "logout"
        url = self.url_base + method
        params = dict(auth=self.auth)
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not logout from pcloud. Status: {s}, reason: {rsn}.".format(s=r.status_code, rsn=r.reason)
            logging.error(msg)
        else:
            res = r.json()
            if res["auth_deleted"]:
                msg = "Logout as required"
            else:
                msg = "Logout not successful, status code: {status}".format(status=r.status_code)
            logging.info(msg)
