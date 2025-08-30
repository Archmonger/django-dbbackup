import shlex

from dbbackup.db.base import BaseCommandDBConnector


class MysqlDumpConnector(BaseCommandDBConnector):
    """
    MySQL connector, creates dump with ``mysqldump`` and restore with
    ``mysql``.
    """

    dump_cmd = "mysqldump"
    restore_cmd = "mysql"

    def _create_dump(self):
        cmd = f"{self.dump_cmd} {self.settings['NAME']} --quick"
        if self.settings.get("HOST"):
            cmd += f" --host={self.settings['HOST']}"
        if self.settings.get("PORT"):
            cmd += f" --port={self.settings['PORT']}"
        if self.settings.get("USER"):
            cmd += f" --user={self.settings['USER']}"
        if self.settings.get("PASSWORD"):
            cmd += f" --password={shlex.quote(self.settings['PASSWORD'])}"

        for table in self.exclude:
            cmd += f" --ignore-table={self.settings['NAME']}.{table}"
        cmd = f"{self.dump_prefix} {cmd} {self.dump_suffix}"
        stdout, stderr = self.run_command(cmd, env=self.dump_env)
        return stdout

    def _restore_dump(self, dump):
        cmd = f"{self.restore_cmd} {self.settings['NAME']}"
        if self.settings.get("HOST"):
            cmd += f" --host={self.settings['HOST']}"
        if self.settings.get("PORT"):
            cmd += f" --port={self.settings['PORT']}"
        if self.settings.get("USER"):
            cmd += f" --user={self.settings['USER']}"
        if self.settings.get("PASSWORD"):
            cmd += f" --password={shlex.quote(self.settings['PASSWORD'])}"

        cmd = f"{self.restore_prefix} {cmd} {self.restore_suffix}"
        stdout, stderr = self.run_command(cmd, stdin=dump, env=self.restore_env)
        return stdout, stderr
