import os
import requests
from flask import current_app


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
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        else:
            current_app.logger.debug("Connected to pcloud")
        # Status Code OK, so successful login
        res = r.json()
        self.auth = res["auth"]
        usedquota = res["usedquota"]
        quota = res["quota"]
        pct = (usedquota/quota)*100
        msg = "{pct:.2f}% used.".format(pct=pct)
        current_app.logger.debug(msg)

    def close_connection(self):
        """
        Logout from pcloud and close connection.

        :return:
        """
        headers = dict(Connection='close')
        method = "logout"
        url = self.url_base + method
        r = self.session.get(url, headers=headers)
        if r.status_code != 200:
            msg = "Could not close connection. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so connection close successful.
        res = r.json()
        return res

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
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        else:
            current_app.logger.debug("File is closed")
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
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res

    def folder_contents(self, folderid=None, foldername=None):
        """
        This method gets a pcloud folder ID and returns a dictionary with sub-directory contents and a dictionary with
        file contents

        :param folderid: ID of the folder (preferred)
        :param foldername: Name of the folder.
        :return: subdirectory contents, files contents
        """
        subdirs = {}
        files = {}
        res = self.listfolder(folderid, foldername)
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
        size = file["size"]
        current_app.logger.debug("File {}, ID {} open with File descriptor {} and size".format(file["name"], file_id,
                                                                                               fd, size))
        # Get file contents
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
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res

    def get_public_cloud_id(self):
        """
        This method returns the ID of the public folder.

        :return: ID of the public folder.
        """
        subdirs, _ = self.folder_contents(foldername="/")
        return subdirs["Public Folder"]["folderid"]

    def listfolder(self, folderid=None, foldername=None):
        """
        This method will get a folder ID and return json string with folder information.

        :param folderid: ID of the folder for which the info is required (int)
        :param foldername: Name of the folder (string).
        :return:
        """
        # Todo: merge method with get_contents method.
        if folderid:
            params = dict(folderid=folderid)
        elif foldername:
            params = dict(path=foldername)
        else:
            current_app.logger.error("Listfolder called without specifying foldername or ID")
            return
        method = "listfolder"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not collect metadata. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res

    def logout(self):
        """
        Logout from pcloud, but keep session.

        :return:
        """
        method = "logout"
        url = self.url_base + method
        params = dict(auth=self.auth)
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not logout from pcloud. Status: {s}, reason: {rsn}.".format(s=r.status_code, rsn=r.reason)
            current_app.logger.error(msg)
        else:
            res = r.json()
            if res["auth_deleted"]:
                msg = "Logout as required"
            else:
                msg = "Logout not successful, status code: {status}".format(status=r.status_code)
            current_app.logger.info(msg)

    def movefile(self, fileid, tofolderid, filename):
        """
        This method copies a file to a destination folder.

        :param fileid: ID of the file to be copied.
        :param tofolderid: Target folder.
        :param filename: Target file name.
        :return:
        """
        params = dict(fileid=fileid, tofolderid=tofolderid, toname=filename)
        method = "renamefile"
        url = self.url_base + method
        r = self.session.get(url, params=params)
        if r.status_code != 200:
            msg = "Could not move file. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res

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
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        else:
            current_app.logger.debug("File has been read")
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
        files = {file: open(ffn, 'rb')}
        params = dict(folderid=folderid)
        method = "uploadfile"
        url = self.url_base + method
        r = self.session.post(url, files=files, params=params)
        if r.status_code != 200:
            msg = "Could not upload file. Status: {s}, reason: {reason}.".format(s=r.status_code, reason=r.reason)
            current_app.logger.critical(msg)
            raise SystemExit(msg)
        # Status Code OK, so successful login
        res = r.json()
        return res
