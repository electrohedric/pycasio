from typing import Protocol
from .context import CasioContext

class SupportsAST(Protocol):
    lineno: int
    col_offset: int
    end_col_offset: int


class CasioException(Exception):
    def __init__(self, ctx: CasioContext, lineinfo: SupportsAST, msg: str, helptxt: str = None):
        lines = ctx.source.splitlines()
        self.file = ctx.filename
        self.line = "<Invalid lineno>"
        self.col_offset = self.end_col_offset = -1
        if hasattr(lineinfo, "lineno"):
            self.lineno = lineinfo.lineno
            if len(lines) >= self.lineno:
                self.line = lines[self.lineno - 1]
            if hasattr(lineinfo, "col_offset"):
                self.col_offset = lineinfo.col_offset
                if hasattr(lineinfo, "end_col_offset"):
                    self.end_col_offset = lineinfo.end_col_offset
                else:
                    self.end_col_offset = len(self.line)
        self.msg = msg
        self.helptxt = f"\nHelp:\n{helptxt}" if helptxt else ""

    def __str__(self):
        HEADER = f"{'=' * 20} CASIO COMPILER {'=' * 20}"
        linespan = ''
        if self.end_col_offset != -1:
            span = max(self.end_col_offset - self.col_offset, 0)
            linespan = f"\n{' ' * self.col_offset}^{'~' * span}"
        return f"\n{HEADER}\nIn file {self.file}:\nLine {self.lineno}:\n{self.line}{linespan}\nError: {self.msg}{self.helptxt}"

class CasioImportException(CasioException):
    pass

class CasioNameError(CasioException):
    pass