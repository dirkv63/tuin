import logging
import os
import requests


class PcloudHandler:

    """
    This class consolidates the pcloud functionality. On initialization a connection to pcloud account is set.
    List method allows to list all files in the specified folder. Logout method will close the connection.
    """

    def __init__(self):
        """
        On initialization a connection to pcloud account is done.
        """
        user = os.getenv("PCLOUD_USER")
        passwd = os.getenv("PCLOUD_PWD")
        params = dict(username=user, password=passwd, getauth=1)
        self.url_base = os.getenv("PCLOUD_HOME")
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

    def close_file(self, file_desc):
        """
        This method closes the file with pcloud file ID file_id.

        :param file_desc: pcloud file descriptor
        :return: binary contents of the file
        """
        params = dict(fd=file_desc)
        method = "file_close"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not open file. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            logging.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res

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

    def folder_contents(self, folderid):
        """
        This method gets a pcloud folder ID and returns a dictionary with sub-directory contents and a dictionary with
        file contents
        :param folderid:
        :return: subdirectory contents, files contents
        """
        subdirs = {}
        files = {}
        res = self.listfolder(folderid)
        contents = res["metadata"]["contents"]
        for content in contents:
            name = content["name"]
            if content["isfolder"]:
                subdirs[name] = content
            else:
                files[name] = content
        return subdirs, files

    def get_content(self, file):
        """
        This method returns the contents of the file.

        :param file: Dictionary with file information.
        :return: (binary) contents of the file.
        """
        file_id = file["fileid"]
        file_desc = self.get_file(file["fileid"])
        fd = file_desc["fd"]
        logging.debug("File {}, ID {} open with File descriptor {}".format(file["name"], file_id, fd))
        # Get file contents
        size = file["size"]
        contents = self.read_file(fd, size)
        # Close file
        self.close_file(fd)
        return contents

    def get_file(self, file_id):
        """
        This method opens the file with ID file_id on pcloud..

        :param file_id: pcloud file ID
        :return: Result of the open operation. Json string with 'fd' as file descriptor.
        """
        params = dict(fileid=file_id, flags=0)
        method = "file_open"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not open file. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
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

    def read_file(self, file_desc, size):
        """
        This method reads the file with descriptor ID file_desc and size on pcloud..

        :param file_desc: pcloud file descriptor.
        :param size: Size of the file to be read.
        :return: Contents of the file.
        """
        params = dict(fd=file_desc, count=size)
        method = "file_read"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not open file. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            logging.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.content
        return res

    def upload_file(self, file, ffn, folderid):
        """
        This method loads file on full filename ffn to folderid.

        :param file: Target File name.
        :param ffn: Full File name (including path) to the file.
        :param folderid: pcloud target folderid.
        :return:
        """
        print(file)
        print(ffn)
        files = {file: open(ffn, 'rb')}
        params = dict(folderid=folderid)
        method = "uploadfile"
        url = self.url_base + method
        r = self.session.post(url, files=files, params=params)
        if r.status_code != 200:
            msg = "Could not upload file. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            logging.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res
