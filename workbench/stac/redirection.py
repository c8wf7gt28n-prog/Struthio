"""staC's bounded UNIX-style I/O syntax and private file access.

The OS shell may redirect staC's real file descriptors anywhere the invoking
user is authorized. Inside the staC REPL / quoted CLI program, we deliberately
support a *bounded* file-redirection dialect:

  program > file.txt           overwrite local export atomically
  program >> file.ndjson       append one output record
  program 2> diagnostics.txt   replace local diagnostic export
  program 2>> diagnostics.txt  append diagnostics
  < name.stac                 read an existing, single-line staC program

Internal filenames are single basenames restricted to Ledger's private
`.ledger/stac/io/{exports,scripts}/` directories. The caller's Kernel scope
still governs hardware, firmware, and vendor reads. The I/O plan describes
presentation separately from the typed IR.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shlex
import stat
import secrets

from .language import Context, MEASURE, _compile_tokenized, _lex_tokens, compile_text

# Explicit, portable simple filenames only. No directories, symlinks or hidden
# entries; rich user paths remain available through the surrounding UNIX shell.
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
ALLOWED_EXPORT_EXT = {'.json', '.ndjson', '.txt', '.log'}
SHELL_META = {';', '&&', '&', '`', '$', '(', ')', '||', '<<', '<>', '>&', '<&'}
MAX_PROGRAM_BYTES = 4096
MAX_EXPORT_BYTES = 4_000_000


class RedirectError(ValueError):
    pass


@dataclass(frozen=True)
class StreamRedirect:
    fd: int
    append: bool
    name: str


@dataclass(frozen=True)
class IOPlan:
    # Exactly one of `program` and `script` is present.
    program: str | None
    script: str | None
    stdout: StreamRedirect | None = None
    stderr: StreamRedirect | None = None
    _tokens: tuple[str, ...] | None = field(default=None, repr=False, compare=False)

    def compile_inline(self, initial_context: Context | None = None) -> dict:
        if self._tokens is None:
            return compile_text(self.program or '', initial_context)
        return _compile_tokenized(self.program, self._tokens, initial_context)


def _filename(name: str, extensions: set[str]) -> str:
    if (not NAME.fullmatch(name) or name in ('.', '..') or name.startswith('.')
            or Path(name).suffix.lower() not in extensions):
        raise RedirectError('INVALID_REDIRECTION_FILENAME: use a simple name with '+', '.join(sorted(extensions)))
    return name


def _lex(line: str) -> list[str]:
    if not isinstance(line,str) or not line.strip() or len(line.encode('utf-8')) > MAX_PROGRAM_BYTES:
        raise RedirectError('Expected a staC program of at most 4096 UTF-8 bytes')
    if any(ch in line for ch in ('\x00','\r','\n')):
        raise RedirectError('One line per staC program')
    try:
        tokens = _lex_tokens(line)
    except ValueError as exc:
        raise RedirectError('Malformed staC quoting: '+str(exc)) from exc
    if len(tokens)>90:
        raise RedirectError('Too many tokens')
    return tokens


def parse(line: str) -> IOPlan:
    """Extract terminal I/O redirections without changing underlying IR.

    `compare > 3us` is a numerical predicate, but `compare > 3us > out.json`
    exports a result. `2>` and `2>>` are explicit stderr, not comparisons.
    """
    toks=_lex(line)
    outs={}
    # Only *terminal* redirects are supported. Parsing from the right avoids
    # ambiguous >= and <= tokens in typed compare expressions.
    while len(toks)>=2:
        name=toks[-1]
        if len(toks)>=3 and toks[-3]=='2' and toks[-2] in ('>', '>>'):
            fd=2;operator=toks[-2]; count=3
        elif len(toks)>=3 and toks[-3]=='1' and toks[-2] in ('>', '>>'):
            fd=1;operator=toks[-2]; count=3
        elif toks[-2] in ('>', '>>'):
            fd=1;operator=toks[-2]; count=2
        else:break
        # Leave a final `compare > 3us` for typed quantity validation.
        if (fd==1 and count==2 and operator=='>' and
                MEASURE.fullmatch(name)):
            break
        name=_filename(name,ALLOWED_EXPORT_EXT)
        if fd in outs:
            raise RedirectError('Only one destination per output descriptor (1 or 2)')
        outs[fd]=StreamRedirect(fd,operator=='>>',name)
        del toks[-count:]
    if any(t in SHELL_META for t in toks):
        raise RedirectError('No shell evaluation, command substitution, fd duplication or here-documents')
    script=None
    if toks and toks[0]=='<':
        if len(toks)!=2:
            raise RedirectError('Input redirection must be < NAME.stac alone (plus terminal output redirects)')
        script=_filename(toks[1],{'.stac'})
        toks=[]
    if not toks and script is None:
        raise RedirectError('No staC program or input script')
    # Keep canonical text for callers and the original tokens for typed compilation.
    program = shlex.join(toks) if script is None else None
    return IOPlan(program, script, outs.get(1), outs.get(2), tuple(toks) if script is None else None)


def _directory(root: Path, category: str, create: bool) -> int:
    """Return fd to an in-root private dir while refusing symlink traversals.

    `root` itself is explicitly selected by the caller. All child components
    use directory FDs and O_NOFOLLOW, including the pre-existing .ledger.
    """
    if category not in ('scripts','exports'):
        raise RedirectError('INVALID_IO_CATEGORY')
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
    fd=os.open(root,flags)
    try:
        for part in ('.ledger','stac','io',category):
            if create:
                try:os.mkdir(part,mode=0o700,dir_fd=fd)
                except FileExistsError:pass
            try:other=os.open(part,flags,dir_fd=fd)
            except (FileNotFoundError,NotADirectoryError,OSError) as exc:
                raise RedirectError('UNAVAILABLE_OR_UNSAFE_IO_DIRECTORY: '+part) from exc
            os.close(fd);fd=other
        return fd
    except BaseException:
        os.close(fd)
        raise


def script_text(root: Path, name: str) -> str:
    name=_filename(name,{'.stac'})
    fd=_directory(root,'scripts',create=False)
    try:
        try:src=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
        except OSError as exc:
            raise RedirectError('SCRIPT_UNAVAILABLE_OR_UNSAFE: '+name) from exc
        try:
            s=os.fstat(src)
            if not stat.S_ISREG(s.st_mode) or s.st_nlink>1 or s.st_size>MAX_PROGRAM_BYTES:
                raise RedirectError('Script must be a single regular file of at most 4096 bytes')
            raw=os.read(src,MAX_PROGRAM_BYTES+1)
        finally:os.close(src)
    finally:os.close(fd)
    if len(raw)>MAX_PROGRAM_BYTES:
        raise RedirectError('SCRIPT_TOO_LARGE')
    try:program=raw.decode('utf-8')
    except UnicodeDecodeError as exc:raise RedirectError('SCRIPT_NOT_UTF8') from exc
    if program.endswith('\r\n'):program=program[:-2]
    elif program.endswith('\n'):program=program[:-1]
    if '\n' in program or '\r' in program:
        raise RedirectError('Only single-line staC scripts are supported')
    return program


def stdin_text(source) -> str:
    """Support ordinary host UNIX input redirection: `stac run - < script`."""
    program=source.read(MAX_PROGRAM_BYTES+1)
    if len(program.encode('utf-8'))>MAX_PROGRAM_BYTES:
        raise RedirectError('INPUT_PROGRAM_TOO_LARGE')
    if program.endswith('\r\n'):program=program[:-2]
    elif program.endswith('\n'):program=program[:-1]
    if not program.strip() or any(c in program for c in ('\r','\n','\x00')):
        raise RedirectError('Only a single staC program is permitted from stdin')
    return program


def export(root: Path, dest: StreamRedirect, content: str) -> Path:
    """Write only in the project-private export dir; prevent symlink/hardlink writes."""
    name=_filename(dest.name,ALLOWED_EXPORT_EXT)
    if not isinstance(content,str):raise RedirectError('INVALID_EXPORT_CONTENT')
    data=content.encode('utf-8')
    if len(data)>MAX_EXPORT_BYTES:raise RedirectError('EXPORT_TOO_LARGE')
    fd=_directory(root,'exports',create=True)
    flags=os.O_WRONLY|os.O_CREAT|os.O_CLOEXEC|os.O_NOFOLLOW
    try:
        if dest.append:
            try:f=os.open(name,flags|os.O_APPEND,0o600,dir_fd=fd)
            except OSError as exc:raise RedirectError('APPEND_TARGET_UNSAFE') from exc
            try:
                s=os.fstat(f)
                if not stat.S_ISREG(s.st_mode) or s.st_nlink>1:
                    raise RedirectError('APPEND_TARGET_NOT_PRIVATE_REGULAR_FILE')
                with os.fdopen(f,'ab',closefd=False) as out:
                    out.write(data)
                    out.flush()
            finally:os.close(f)
        else:
            # `>` creates a new file and atomically replaces the old export
            # entry. It never follows links to canonical source files.
            tmp_name='.stac-export-'+secrets.token_hex(12)
            tmp_fd=None
            try:
                tmp_fd=os.open(tmp_name,flags|os.O_EXCL,0o600,dir_fd=fd)
                with os.fdopen(tmp_fd,'wb',closefd=False) as out:
                    out.write(data)
                    out.flush()
                    os.fsync(out.fileno())
                os.close(tmp_fd);tmp_fd=None
                os.replace(tmp_name,name,src_dir_fd=fd,dst_dir_fd=fd)
            finally:
                if tmp_fd is not None:os.close(tmp_fd)
                try:os.unlink(tmp_name,dir_fd=fd)
                except FileNotFoundError:pass
    finally:os.close(fd)
    return root/'.ledger'/'stac'/'io'/'exports'/name
