import shlex

from dbbackup.db.base import BaseCommandDBConnector


class MongoDumpConnector(BaseCommandDBConnector):
    """
    MongoDB connector, creates dump with ``mongodump`` and restore with
    ``mongorestore``.
    """

    dump_cmd = "mongodump"
    restore_cmd = "mongorestore"
    object_check = True
    drop = True

    def _create_dump(self):
        cmd = f"{self.dump_cmd} --db {self.settings['NAME']}"
        host = self.settings.get("HOST") or "localhost"
        port = self.settings.get("PORT") or 27017
        cmd += f" --host {host}:{port}"
        if self.settings.get("USER"):
            cmd += f" --username {self.settings['USER']}"
        if self.settings.get("PASSWORD"):
            cmd += f" --password {shlex.quote(self.settings['PASSWORD'])}"

        if self.settings.get("AUTH_SOURCE"):
            cmd += f" --authenticationDatabase {self.settings['AUTH_SOURCE']}"
        for collection in self.exclude:
            cmd += f" --excludeCollection {collection}"
        cmd += " --archive"
        cmd = f"{self.dump_prefix} {cmd} {self.dump_suffix}"
        stdout, stderr = self.run_command(cmd, env=self.dump_env)
        return stdout

    def _restore_dump(self, dump):
        cmd = self.restore_cmd
        host = self.settings.get("HOST") or "localhost"
        port = self.settings.get("PORT") or 27017
        cmd += f" --host {host}:{port}"
        if self.settings.get("USER"):
            cmd += f" --username {self.settings['USER']}"
        if self.settings.get("PASSWORD"):
            cmd += f" --password {shlex.quote(self.settings['PASSWORD'])}"

        if self.settings.get("AUTH_SOURCE"):
            cmd += f" --authenticationDatabase {self.settings['AUTH_SOURCE']}"
        if self.object_check:
            cmd += " --objcheck"
        if self.drop:
            cmd += " --drop"
        cmd += " --archive"
        cmd = f"{self.restore_prefix} {cmd} {self.restore_suffix}"
        return self.run_command(cmd, stdin=dump, env=self.restore_env)
