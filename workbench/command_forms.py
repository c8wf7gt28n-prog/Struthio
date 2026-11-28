"""The command tool's table (Graphite 1.1 KS2): every program she knows and its argument forms, each classed read, change,
destroy, root or network (several may apply). Data only; command_tool.py is the code that reads it.

PLAN_1.1.md, KS2: "a classifier that knows which forms only read, change, destroy, need root or reach the network, and
refuses what it cannot classify". Anything not here (a program, a flag, an operand of a kind no form takes) is refused in
plain words with the exact line shown, and never run.

A FORM is a dict:
  classes   what it does: ('read',), ('change',), ('read', 'network'), ('destroy',), ('root',) ...
  sub       the words that must come first among the operands (a subcommand: apt list, systemctl status)
  opts      the options it takes, written exactly: '-l' stands alone, '-n=N' takes a value of kind N (as -n 5, -n5 or, long,
            --lines=5 / --lines 5); '-#' admits -NUM (head -5). Short options may be run together (ls -lah) when each is
            one of these; a long option is never abbreviated.
  ops       its operands, in order: kinds with * (any), + (one or more) or ? (at most one)
  must      option groups, each of which must be present (ping -c, cp -n): (('-c', '--count'),)
  must_why  the refusal when a group is missing (a code of WHY)
  refused   options it knows and refuses, each with its WHY code (find -delete, sort -o, tail -f)
  says      what it does, for "This will …" (slots: {P} paths read, {W} paths made, {Q} where it lands, {M} a mode, {H} the host,
            {T} the words, {N} the names)
  needs     the system places the seal lets it read beyond the system's own folders (see NEEDS)
  sockets   'none' (default), 'local' (the machine's own channels: the system bus, netlink), 'network' (a network read)
  implicit  'home' when it reads the current folder with no path named (the run's folder is your home)
  plan      for a change: how command_tool plans, verifies and undoes it
  check     a further check in command_tool (find's expression, ps's BSD words, ip's showing forms, a mode ...)
  refuse    a form that is known and refused as a whole: its WHY code
  seconds   how long it may run (default 30)

KINDS of a value or an operand:
  P a path it reads · W a path it makes (must not be there) · Q where a copy, move or link lands (a folder that is there, or
  a new name) · D a folder it writes into · T words · N a whole number · I an interval (0.2 to 60) · C a list (columns,
  fields) · H a host · U a web address (http or https) · M a mode for chmod · K a name (a package, a program, a unit)
  · X exactly '-' (standard output) · O cp's --update that never writes over (none, none-fail)
"""

R, C, D, ROOT, NET = 'read', 'change', 'destroy', 'root', 'network'

# Places a read may need beyond SYSTEM_READ (command_seal): each a key of a form's `needs`.
NEEDS = {'proc': ('/proc',), 'sys': ('/sys', '/run/udev'), 'journal': ('/var/log/journal', '/run/log/journal', '/var/log'),
         'apt': ('/var/lib/apt', '/var/cache/apt', '/var/lib/dpkg', '/var/log/apt'), 'dpkg': ('/var/lib/dpkg',),
         'run': ('/run', '/var/run', '/var/log/wtmp', '/var/lib/systemd'), 'man': ('/var/cache/man',),
         'usb': ('/sys', '/run/udev', '/var/lib/usbutils'), 'pci': ('/sys', '/run/udev', '/var/lib/pciutils')}

# Why a form or an option is refused, in plain words (her talk says "Refused, and nothing ran: " first).
WHY = {
    'root': 'it needs root, the administrator. That is the system door, which comes in the next slice of this preview.',
    'destroy': 'it removes for good, with no way back. I do not run it here.',
    'never_ends': 'it never ends by itself, so it would hold the run. Give it an end (a count) or use your Terminal.',
    'session': 'it opens a session on another computer, and what runs there I cannot classify. It is yours, in your Terminal.',
    'sends_files': 'it sends or copies files between computers. That is not offered here; it is yours, in your Terminal.',
    'saves_fetch': 'it saves what it fetches as a file. Here a fetch is shown as data only (curl -s, or wget -q -O -).',
    'sends_data': 'it sends data, a form or a password to another computer. I do not send that from a command.',
    'writes_file': 'that option writes a file the form does not show. Here a read writes nothing.',
    'runs_program': 'that option runs another program, which I cannot classify.',
    'overwrites': 'it can write over a file of the same name. With -n it leaves what is there, and Undo can take it back.',
    'hard_link': 'a hard link cannot be told from the file. Here a link is ln -s.',
    'recursive_mode': 'chmod -R changes every file under the folder. Name the files instead.',
    'special_bits': 'setuid, setgid and the sticky bit are the system door’s, not a change of your files.',
    'no_extract': 'unzip without -l unpacks, and writes files. Ask for the recipe Unzip: it shows what it makes, with Undo.',
    'perl_code': 'rename takes Perl code. Here only a plain s/old/new/ of letters, digits, spaces, dots and dashes is read.',
    'network_names': 'that option asks a server on the network, and this form only reads this computer.',
    'insecure': 'that option turns off the check of the other computer’s certificate.',
    'ask_tty': 'it asks questions on a terminal, and a run here has none.',
    'not_preserve_root': 'never: that is the whole system.',
    'remote_shell': 'that option names a program to reach the other computer with, which I cannot classify.',
}

F = dict      # a form is a plain dict

TABLE = {
    # ---- reads: files ----------------------------------------------------------------------------------------------------
    'ls': [F(classes=(R,), opts='-a -A -l -h -R -t -S -r -1 -d -i -s -F -p -n -g -o -G -L -U -X -v -c -u -Q -C -m -x -k -N --all '
             '--almost-all --human-readable --si --recursive --reverse --directory --inode --size --classify --numeric-uid-gid '
             '--dereference --group-directories-first --full-time --author --literal --color=T --sort=T --time-style=T --time=T '
             '--format=T --block-size=T --ignore=T --hide=T -I=T --width=N -w=N --quoting-style=T --indicator-style=T',
             ops='P*', implicit='home', says='list what is in {P}')],
    'cat': [F(classes=(R,), opts='-n -b -s -A -v -E -T -e -t -u --number --number-nonblank --squeeze-blank --show-all --show-ends '
              '--show-tabs --show-nonprinting', ops='P+', says='show what {P} holds')],
    'head': [F(classes=(R,), opts='-n=N -c=N -q -v -z --lines=N --bytes=N --quiet --silent --verbose --zero-terminated -#', ops='P+',
               says='show the first lines of {P}')],
    'tail': [F(classes=(R,), opts='-n=N -c=N -q -v -z --lines=N --bytes=N --quiet --silent --verbose --zero-terminated -#', ops='P+',
               refused={'-f': 'never_ends', '-F': 'never_ends', '--follow': 'never_ends', '--retry': 'never_ends', '--pid': 'never_ends',
                        '-s': 'never_ends', '--sleep-interval': 'never_ends'}, says='show the last lines of {P}')],
    'wc': [F(classes=(R,), opts='-l -w -c -m -L --lines --words --bytes --chars --max-line-length', ops='P+', says='count the lines, words and bytes of {P}')],
    'stat': [F(classes=(R,), opts='-L -f -t -c=T --format=T --printf=T --dereference --file-system --terse', ops='P+', says='show the details of {P}')],
    'file': [F(classes=(R,), opts='-b -i -L -h -z -k -p -s -N -0 -E --brief --mime --mime-type --mime-encoding --dereference '
               '--no-dereference --uncompress --keep-going --special-files --no-pad --print0', ops='P+', says='say what kind of file {P} is')],
    'du': [F(classes=(R,), opts='-a -b -c -h -H -k -L -l -m -P -s -S -x -D -0 --all --apparent-size --bytes --total --human-readable '
             '--si --dereference --count-links --separate-dirs --summarize --one-file-system --time --inodes --null -d=N --max-depth=N '
             '--exclude=T -B=T --block-size=T -t=T --threshold=T --time-style=T', ops='P*', implicit='home', seconds=120,
             says='add up what takes the space in {P}')],
    'df': [F(classes=(R,), opts='-a -h -H -i -k -l -P -T --all --human-readable --si --inodes --local --portability --print-type '
             '--total --output -B=T --block-size=T -t=T --type=T -x=T --exclude-type=T --output=C', ops='P*', needs=('proc',),
             says='show how full each disk is')],
    'tree': [F(classes=(R,), opts='-a -d -f -i -h -s -D -F -p -u -g -C -n --du --noreport --dirsfirst -L=N --filelimit=N -I=T -P=T',
               ops='P*', implicit='home', says='draw the folders under {P}')],
    'realpath': [F(classes=(R,), opts='-e -m -s -q -L -P -z --canonicalize-existing --canonicalize-missing --no-symlinks --quiet', ops='P+',
                   says='show the full path of {P}')],
    'readlink': [F(classes=(R,), opts='-f -e -m -n -q -s -v -z --canonicalize --canonicalize-existing --canonicalize-missing --no-newline',
                   ops='P+', says='show where the link {P} points')],
    'find': [F(classes=(R,), check='find', implicit='home', seconds=120, says='look for files under {P}')],
    'grep': [F(classes=(R,), opts='-i -y -v -w -x -c -l -L -n -h -H -o -q -s -r -R -E -F -G -P -z -Z -a -I -U -T -b --ignore-case '
               '--no-ignore-case --invert-match --word-regexp --line-regexp --count --files-with-matches --files-without-match '
               '--line-number --no-filename --with-filename --only-matching --quiet --silent --no-messages --recursive '
               '--dereference-recursive --extended-regexp --fixed-strings --basic-regexp --perl-regexp --null-data --null --text '
               '--initial-tab --byte-offset --color=T --colour=T -e=T --regexp=T -f=P --file=P -m=N --max-count=N -A=N -B=N -C=N '
               '--after-context=N --before-context=N --context=N --include=T --exclude=T --exclude-dir=T --label=T -#',
               ops='T P*', pattern_by=('-e', '--regexp', '-f', '--file'), implicit='home', seconds=120, says='look for {T} in {P}')],
    'sort': [F(classes=(R,), opts='-b -d -f -g -i -M -h -n -R -r -V -c -C -m -s -u -z -k=T -t=T --ignore-leading-blanks --dictionary-order '
               '--ignore-case --general-numeric-sort --ignore-nonprinting --month-sort --human-numeric-sort --numeric-sort --random-sort '
               '--reverse --version-sort --check --merge --stable --unique --zero-terminated --key=T --field-separator=T --sort=T',
               ops='P+', refused={'-o': 'writes_file', '--output': 'writes_file', '-T': 'writes_file', '--temporary-directory': 'writes_file',
                                  '--compress-program': 'runs_program', '--files0-from': 'writes_file'}, says='show the lines of {P} in order')],
    'uniq': [F(classes=(R,), opts='-c -d -D -u -i -z -f=N -s=N -w=N --count --repeated --unique --ignore-case --zero-terminated '
               '--skip-fields=N --skip-chars=N --check-chars=N', ops='P', too_many='writes_file', says='show the lines of {P} without repeats')],
    'cut': [F(classes=(R,), opts='-d=T -f=C -c=C -b=C -s -z --delimiter=T --fields=C --characters=C --bytes=C --only-delimited --complement '
              '--output-delimiter=T --zero-terminated', ops='P+', says='show some columns of {P}')],
    'diff': [F(classes=(R,), opts='-u -c -q -s -r -N -i -w -b -B -E -Z -y -t -T -a -U=N -C=N -x=T -W=N --brief --report-identical-files '
               '--recursive --new-file --ignore-case --ignore-all-space --ignore-space-change --ignore-blank-lines --side-by-side --text '
               '--unified=N --context=N --color=T --exclude=T --width=N --suppress-common-lines --normal --expand-tabs',
               ops='P P', says='show how {P} differ')],
    'cmp': [F(classes=(R,), opts='-b -l -s -n=N --print-bytes --verbose --quiet --silent --bytes=N', ops='P P', says='compare {P} byte by byte')],
    'comm': [F(classes=(R,), opts='-1 -2 -3 -i --check-order --nocheck-order --total -z --zero-terminated --output-delimiter=T', ops='P P',
               says='show the lines {P} share')],
    'strings': [F(classes=(R,), opts='-a -d -f -w -n=N -t=T -e=T --all --data --print-file-name --bytes=N --radix=T --encoding=T', ops='P+',
                  says='show the readable text inside {P}')],
    'xxd': [F(classes=(R,), opts='-a -b -e -i -p -u -l=N -s=N -c=N -g=N -o=N', ops='P', too_many='writes_file', says='show {P} as hex')],
    'hexdump': [F(classes=(R,), opts='-b -c -C -d -o -x -v -n=N -s=N', ops='P+', says='show {P} as hex')],
    'sha256sum': [F(classes=(R,), opts='-b -t -z -c -w --binary --text --tag --zero --check --quiet --status --strict --warn --ignore-missing',
                    ops='P+', implicit='home', says='work out the SHA-256 of {P}')],
    'sha1sum': [F(classes=(R,), opts='-b -t -z -c -w --binary --text --tag --zero --check --quiet --status --strict --warn --ignore-missing',
                  ops='P+', implicit='home', says='work out the SHA-1 of {P}')],
    'sha512sum': [F(classes=(R,), opts='-b -t -z -c -w --binary --text --tag --zero --check --quiet --status --strict --warn --ignore-missing',
                    ops='P+', implicit='home', says='work out the SHA-512 of {P}')],
    'md5sum': [F(classes=(R,), opts='-b -t -z -c -w --binary --text --tag --zero --check --quiet --status --strict --warn --ignore-missing',
                 ops='P+', implicit='home', says='work out the MD5 of {P}')],
    'b2sum': [F(classes=(R,), opts='-b -t -z -c -w -l=N --length=N --binary --text --tag --zero --check --quiet --status --strict --warn',
                ops='P+', implicit='home', says='work out the BLAKE2 of {P}')],
    'unzip': [F(classes=(R,), opts='-l -v -Z -t -q -qq -z', must=(('-l', '-v', '-Z', '-t'),), must_why='no_extract', ops='P T*',
                says='list what is inside {P}')],
    'zipinfo': [F(classes=(R,), opts='-1 -2 -s -m -l -v -h -t -T -z -M', ops='P T*', says='list what is inside {P}')],
    'tar': [F(classes=(R,), opts='-t --list -v --verbose -z --gzip -j --bzip2 -J --xz --zstd --lzma -a --auto-compress -f=P --file=P '
              '--numeric-owner --full-time', must=(('-t', '--list'), ('-f', '--file')), ops='T*', says='list what is inside {P}'),
            F(classes=(C,), opts='-c --create -v --verbose -z --gzip -j --bzip2 -J --xz --zstd -a --auto-compress -f=W --file=W --exclude=T',
              must=(('-c', '--create'), ('-f', '--file')), ops='P+', plan='tar_c', says='make the archive {W} of {P}'),
            F(classes=(C,), opts='-x --extract --get -v --verbose -z --gzip -j --bzip2 -J --xz --zstd --lzma -a -f=P --file=P -C=D '
              '--directory=D -k --keep-old-files --skip-old-files --no-same-owner --no-same-permissions --one-top-level',
              must=(('-x', '--extract', '--get'), ('-f', '--file')), ops='T*', plan='tar_x', says='unpack {P} into {Q}',
              refused={'--overwrite': 'overwrites', '--unlink-first': 'overwrites', '-U': 'overwrites', '--recursive-unlink': 'overwrites',
                       '--absolute-names': 'overwrites', '-P': 'overwrites', '--to-command': 'runs_program', '-I': 'runs_program',
                       '--use-compress-program': 'runs_program', '--checkpoint-action': 'runs_program', '--rsh-command': 'remote_shell',
                       '-F': 'runs_program', '--info-script': 'runs_program', '--new-volume-script': 'runs_program'})],
    # ---- reads: the computer -----------------------------------------------------------------------------------------------
    'lsblk': [F(classes=(R,), opts='-a -b -d -D -f -J -l -m -n -p -P -r -S -t -z -O -T --all --bytes --nodeps --discard --fs --json --list '
                '--perms --noheadings --paths --pairs --raw --scsi --topology --output-all --tree -o=C --output=C -e=C -I=C -x=T --sort=T',
                ops='P*', needs=('sys', 'proc'), says='list the disks and their parts')],
    'findmnt': [F(classes=(R,), opts='-a -A -b -D -f -J -k -l -m -n -r -R -s -u -U -v --all --ascii --bytes --df --first-only --json --kernel '
                  '--list --mtab --noheadings --raw --submounts --fstab --notruncate --uniq --nofsroot --real --pseudo -o=C --output=C '
                  '-t=C --types=C -O=C --options=C -S=T --source=T -T=P --target=P -M=P --mountpoint=P', ops='T*', needs=('proc', 'sys'),
                  says='list what is mounted')],
    'free': [F(classes=(R,), opts='-b -k -m -g -h -l -t -v -w --bytes --kilo --mega --giga --tera --kibi --mebi --gibi --tebi --human --si '
               '--lohi --total --committed --wide', refused={'-s': 'never_ends', '--seconds': 'never_ends'}, ops='', needs=('proc',),
               says='show how the memory is used')],
    'uptime': [F(classes=(R,), opts='-p -s --pretty --since', ops='', needs=('proc', 'run'), says='show how long the computer has been up')],
    'ps': [F(classes=(R,), check='ps', needs=('proc',), says='list the running programs')],
    'pgrep': [F(classes=(R,), opts='-a -c -f -i -l -n -o -v -w -x -u=T -U=T -G=T -g=T -P=T -s=T -t=T --list-name --list-full --count --full '
                '--ignore-case --newest --oldest --inverse --lightweight --exact --euid=T --uid=T --parent=T --older=N', ops='T',
                needs=('proc',), says='look for a running program called {T}')],
    'top': [F(classes=(R,), opts='-b -c -H -i -S -O -1 -n=N -E=T -e=T -o=T -w=N -u=T -U=T -p=T -d=I', must=(('-b',), ('-n',)), must_why='never_ends',
              ops='', needs=('proc',), says='take one look at the busiest programs')],
    'ss': [F(classes=(R,), opts='-t -u -l -n -p -a -x -s -4 -6 -H -e -m -o -i -w -0 -A=C -f=T --tcp --udp --listening --numeric --processes '
             '--all --unix --summary --ipv4 --ipv6 --no-header --extended --memory --options --info --raw --packet',
             refused={'-r': 'network_names', '--resolve': 'network_names', '-K': 'root', '--kill': 'root'}, ops='T*', needs=('proc',),
             sockets='local', says='list the network connections and listening ports of this computer')],
    'ip': [F(classes=(R,), check='ip', sockets='local', needs=('proc', 'sys'), says='show the network setup of this computer'),
           F(classes=(ROOT,), refuse='root')],
    'journalctl': [F(classes=(R,), opts='-b -k -e -r -x -a -q -m --boot --dmesg --pager-end --reverse --catalog --all --quiet --no-pager --utc '
                     '--no-hostname --merge --system --user --list-boots --disk-usage --no-tail -n=N --lines=N -u=T --unit=T -p=T '
                     '--priority=T -S=T --since=T -U=T --until=T -g=T --grep=T -o=T --output=T -t=T --identifier=T --user-unit=T',
                     refused={'-f': 'never_ends', '--follow': 'never_ends', '--vacuum-size': 'root', '--vacuum-time': 'root',
                              '--vacuum-files': 'root', '--rotate': 'root', '--flush': 'root', '--sync': 'root', '--relinquish-var': 'root',
                              '--setup-keys': 'root', '--update-catalog': 'root'},
                     ops='T*', needs=('journal', 'run'), seconds=60, says='read the system’s log')],
    'systemctl': [F(classes=(R,), sub=(sub,), opts='--user --system --no-pager --plain --no-legend --all -a --full -l --failed --value -q --quiet '
                    '-r --recursive --reverse --before --after --type=C -t=C --state=C -n=N --lines=N -o=T --output=T -p=C --property=C',
                    ops='K*', needs=('run',), sockets='local', says='read the state of {N}' if sub in ('status', 'is-active', 'is-enabled', 'is-failed', 'show', 'cat') else 'list the services')
                  for sub in ('status', 'list-units', 'list-unit-files', 'list-timers', 'list-sockets', 'is-active', 'is-enabled', 'is-failed',
                              'show', 'cat', 'list-dependencies', 'get-default')]
                 + [F(classes=(ROOT,), refuse='root')],
    'apt': [F(classes=(R,), sub=('list',), opts='--upgradable --installed --all-versions -a --manual-installed -q --quiet', ops='T*',
              needs=('apt',), seconds=60, says='list the packages'),
            F(classes=(R,), sub=('show',), opts='-a --all-versions -q', ops='K+', needs=('apt',), says='show the package {N}'),
            F(classes=(R,), sub=('policy',), opts='-q', ops='K*', needs=('apt',), says='show which version of {N} is installed and offered'),
            F(classes=(R,), sub=('search',), opts='-n --names-only -f --full -q', ops='T+', needs=('apt',), seconds=60, says='look for packages about {T}'),
            F(classes=(R,), sub=('depends',), opts='-q', ops='K+', needs=('apt',), says='show what {N} needs'),
            F(classes=(R,), sub=('rdepends',), opts='-q', ops='K+', needs=('apt',), says='show what needs {N}'),
            F(classes=(ROOT,), refuse='root')],
    'apt-get': [F(classes=(R,), opts='-s --simulate --just-print --dry-run --no-act --recon -q -qq -V', must=(('-s', '--simulate', '--just-print',
                  '--dry-run', '--no-act', '--recon'),), must_why='root', ops='K+', needs=('apt',), seconds=60, check='apt_get',
                  says='show what “{N}” would change, without changing it'),
                F(classes=(ROOT,), refuse='root')],
    'apt-cache': [F(classes=(R,), sub=(sub,), opts='-n --names-only -f --full -i --important --installed --recurse -q', ops='T*', needs=('apt',),
                    seconds=60, says='read the package lists ({N})')
                  for sub in ('policy', 'show', 'search', 'depends', 'rdepends', 'madison', 'showpkg', 'stats', 'pkgnames', 'showsrc')]
                 + [F(classes=(ROOT,), refuse='root')],
    'dpkg': [F(classes=(R,), opts=mode + ' --no-pager', must=((mode.split()[0], mode.split()[1]),), ops=ops, needs=('dpkg',),
               says=says) for mode, ops, says in (('-l --list', 'T*', 'list the installed packages'), ('-L --listfiles', 'K+', 'list the files of {N}'),
                                                  ('-S --search', 'T+', 'say which package holds {T}'), ('-s --status', 'K+', 'show the state of {N}'),
                                                  ('-p --print-avail', 'K+', 'show what is known of {N}'))]
            + [F(classes=(R,), opts='--print-architecture', must=(('--print-architecture',),), ops='', needs=('dpkg',), says='say this computer’s architecture'),
               F(classes=(R,), opts='--get-selections', must=(('--get-selections',),), ops='T*', needs=('dpkg',), says='list what is selected to install'),
               F(classes=(R,), opts='-c --contents', must=(('-c', '--contents'),), ops='P', says='list what is inside the package file {P}'),
               F(classes=(R,), opts='-I --info', must=(('-I', '--info'),), ops='P', says='show the details of the package file {P}'),
               F(classes=(ROOT,), refuse='root')],
    'which': [F(classes=(R,), opts='-a -s', ops='K+', says='say where the program {N} is')],
    'whereis': [F(classes=(R,), opts='-b -m -s -u -l', ops='K+', needs=('man',), says='say where the program {N}, its source and its manual are')],
    'man': [F(classes=(R,), opts='-w --where --path -f --whatis -a --all -k --apropos', ops='T+', needs=('man',), seconds=60,
              says='read the manual of {T}')],
    'uname': [F(classes=(R,), opts='-a -s -n -r -v -m -p -i -o --all --kernel-name --nodename --kernel-release --kernel-version --machine '
                '--processor --hardware-platform --operating-system', ops='', says='say which system and kernel this is')],
    'lscpu': [F(classes=(R,), opts='-a -b -c -e -p -J -x -y -B -C --all --online --offline --json --hex --physical --bytes --caches '
                '--extended=C --parse=C', ops='', needs=('proc', 'sys'), says='describe the processor')],
    'lsusb': [F(classes=(R,), opts='-v -t -V --verbose --tree -s=T -d=T', ops='', needs=('usb',), says='list the USB devices')],
    'lspci': [F(classes=(R,), opts='-v -k -n -t -D -m -b -x -s=T -d=T', refused={'-q': 'network_names', '-Q': 'network_names'}, ops='',
                needs=('pci',), says='list the PCI devices (the graphics card among them)')],
    'sensors': [F(classes=(R,), opts='-A -u -f -j --no-adapter --fahrenheit --bus-list', ops='T*', needs=('sys',), says='read the temperatures and fans')],
    'lsmod': [F(classes=(R,), opts='', ops='', needs=('proc', 'sys'), says='list the kernel’s modules')],
    'whoami': [F(classes=(R,), opts='', ops='', says='say which user this is')],
    'id': [F(classes=(R,), opts='-u -g -G -n -r -z --user --group --groups --name --real', ops='T?', says='show the user and groups')],
    'nproc': [F(classes=(R,), opts='--all --ignore=N', ops='', needs=('sys', 'proc'), says='count the processors')],
    'pwd': [F(classes=(R,), opts='-L -P', ops='', says='say the folder it runs in (your home)')],
    'date': [F(classes=(R,), opts='-u -R -I --utc --universal --rfc-email --debug -d=T --date=T -r=P --reference=P --iso-8601=T --rfc-3339=T',
               ops='T?', check='date', refused={'-s': 'root', '--set': 'root'}, says='say the date and time'),
             F(classes=(ROOT,), refuse='root')],
    'hostname': [F(classes=(R,), opts='-f -s -d -i -I -A -a -y --fqdn --long --short --domain --ip-address --all-ip-addresses --all-fqdns '
                   '--alias --yp --nis', ops='T?', check='hostname', says='say this computer’s name'),
                 F(classes=(ROOT,), refuse='root')],
    'dmesg': [F(classes=(R,), opts='-T -H -k -u -x -e -t -J --ctime --human --kernel --userspace --decode --reltime --notime --json -l=C '
                '--level=C -f=C --facility=C', refused={'-w': 'never_ends', '--follow': 'never_ends', '-W': 'never_ends', '-c': 'root',
                                                         '-C': 'root', '--clear': 'root', '--read-clear': 'root', '-n': 'root', '-D': 'root', '-E': 'root'},
                ops='', needs=('proc',), says='read the kernel’s messages')],
    'sysctl': [F(classes=(R,), opts='-a -n -N -b -e -q --all --values --names --binary --ignore --quiet', ops='T*', check='sysctl', needs=('proc',),
                 refused={'-w': 'root', '--write': 'root', '-p': 'root', '--load': 'root', '--system': 'root'},
                 says='read the kernel’s settings'),
               F(classes=(ROOT,), refuse='root')],
    # ---- reads that reach the network: each waits for your press, and NET says it while it runs ------------------------------
    'ping': [F(classes=(R, NET), opts='-c=N -W=N -w=N -i=I -s=N -t=N -4 -6 -n -q -D -O --count=N', must=(('-c', '--count'),), must_why='never_ends',
               ops='H', sockets='network', seconds=90, says='send a few pings to {H} and count the answers')],
    'dig': [F(classes=(R, NET), opts='-4 -6 -x=H -t=T -p=N -c=T', ops='T+', check='dig', sockets='network', seconds=60,
              says='ask the name servers about {H}')],
    'host': [F(classes=(R, NET), opts='-a -v -4 -6 -t=T -W=N -R=N', ops='H T?', sockets='network', seconds=60, says='ask the name servers about {H}')],
    'curl': [F(classes=(R, NET), opts='-I -s -S -L -i -f -v --head --silent --show-error --location --include --fail --verbose --compressed '
               '--http1.1 --http2 -4 -6 -m=N --max-time=N --connect-timeout=N -A=T --user-agent=T -r=T --range=T --max-filesize=N '
               '--max-redirs=N -w=T --write-out=T', ops='U', sockets='network', seconds=90,
               refused={'-o': 'saves_fetch', '-O': 'saves_fetch', '--output': 'saves_fetch', '--remote-name': 'saves_fetch', '--output-dir': 'saves_fetch',
                        '-D': 'saves_fetch', '--dump-header': 'saves_fetch', '-c': 'saves_fetch', '--cookie-jar': 'saves_fetch',
                        '-d': 'sends_data', '--data': 'sends_data', '--data-binary': 'sends_data', '--data-raw': 'sends_data', '-F': 'sends_data',
                        '--form': 'sends_data', '-T': 'sends_data', '--upload-file': 'sends_data', '-u': 'sends_data', '--user': 'sends_data',
                        '-X': 'sends_data', '--request': 'sends_data', '-K': 'runs_program', '--config': 'runs_program', '-k': 'insecure',
                        '--insecure': 'insecure'},
               says='fetch {H} and show what it sends back, as data')],
    'wget': [F(classes=(R, NET), opts='-q -S -nv --quiet --server-response --no-verbose -O=X --output-document=X -T=N --timeout=N -t=N --tries=N '
               '-U=T --user-agent=T --max-redirect=N -4 -6', must=(('-O', '--output-document'),), must_why='saves_fetch', ops='U',
               sockets='network', seconds=90, refused={'--post-data': 'sends_data', '--post-file': 'sends_data', '--user': 'sends_data',
                                                        '--password': 'sends_data', '--no-check-certificate': 'insecure'},
               says='fetch {H} and show what it sends back, as data'),
             F(classes=(R, NET), opts='--spider -q -S -nv --quiet --server-response --no-verbose -T=N --timeout=N -t=N --tries=N -4 -6',
               must=(('--spider',),), ops='U', sockets='network', seconds=90, says='ask {H} whether the page is there, without fetching it')],
    'rsync': [F(classes=(R,), check='rsync', opts='-n --dry-run -a -r -v -z -h -i -c --archive --recursive --verbose --compress --human-readable '
                '--itemize-changes --checksum --stats --delete --exclude=T', must=(('-n', '--dry-run'),), must_why='sends_files', ops='T T',
                refused={'-e': 'remote_shell', '--rsh': 'remote_shell', '--rsync-path': 'remote_shell'}, says='show what the copy would do, without copying')],
    'ssh': [F(classes=(NET, C), refuse='session')], 'scp': [F(classes=(NET, C), refuse='sends_files')], 'sftp': [F(classes=(NET, C), refuse='sends_files')],
    'nc': [F(classes=(NET, C), refuse='session')], 'ncat': [F(classes=(NET, C), refuse='session')], 'netcat': [F(classes=(NET, C), refuse='session')],
    'telnet': [F(classes=(NET, C), refuse='session')], 'ftp': [F(classes=(NET, C), refuse='sends_files')], 'mosh': [F(classes=(NET, C), refuse='session')],
    # ---- changes: each shows "This will … / The command: …", waits for your press, is verified on the disk, and has Undo ---------
    'mkdir': [F(classes=(C,), opts='-p -v --parents --verbose -m=M --mode=M', ops='W+', plan='mkdir', says='make the folder {W}')],
    'touch': [F(classes=(C,), opts='-c --no-create', ops='W+', plan='touch', says='make the empty file {W}')],
    'cp': [F(classes=(C,), opts='-n --no-clobber -r -R --recursive -a --archive -p -v --verbose -T --no-target-directory -L -P -d --update=O',
             must=(('-n', '--no-clobber', '--update'),), must_why='overwrites', ops='P+ Q', plan='cp', says='copy {P} to {Q}',
             refused={'-f': 'overwrites', '--force': 'overwrites', '-b': 'overwrites', '--backup': 'overwrites', '--remove-destination': 'overwrites',
                      '-l': 'hard_link', '--link': 'hard_link', '-s': 'overwrites', '--symbolic-link': 'overwrites', '-i': 'ask_tty',
                      '--interactive': 'ask_tty', '-u': 'overwrites', '-t': 'overwrites', '--target-directory': 'overwrites'})],
    'mv': [F(classes=(C,), opts='-n --no-clobber -v --verbose -T --no-target-directory', must=(('-n', '--no-clobber'),), must_why='overwrites',
             ops='P+ Q', plan='mv', says='move {P} to {Q}',
             refused={'-f': 'overwrites', '--force': 'overwrites', '-b': 'overwrites', '--backup': 'overwrites', '-u': 'overwrites', '--update': 'overwrites',
                      '-i': 'ask_tty', '--interactive': 'ask_tty', '-t': 'overwrites', '--target-directory': 'overwrites'})],
    'ln': [F(classes=(C,), opts='-s --symbolic -v --verbose -T --no-target-directory -n --no-dereference', must=(('-s', '--symbolic'),), must_why='hard_link',
             ops='T W', plan='ln', says='make a link {W} that points to {T}',
             refused={'-f': 'overwrites', '--force': 'overwrites', '-b': 'overwrites', '--backup': 'overwrites', '-i': 'ask_tty', '-r': 'hard_link'})],
    'chmod': [F(classes=(C,), opts='-v -c --verbose --changes', ops='M P+', plan='chmod', says='set the mode of {P} to {M}',
                refused={'-R': 'recursive_mode', '--recursive': 'recursive_mode', '--reference': 'writes_file'})],
    'rename.ul': [F(classes=(R,), opts='-v -n -o -l --verbose --no-act --no-overwrite --last', must=(('-n', '--no-act'),), ops='T T P+',
                    says='show how {P} would be renamed (“{A}” to “{B}”), without renaming'),
                  F(classes=(C,), opts='-v -o -l --verbose --no-overwrite --last', ops='T T P+', plan='rename_ul', says='rename {P}: “{A}” becomes “{B}”',
                    refused={'-s': 'overwrites', '--symlink': 'overwrites', '-i': 'ask_tty', '--interactive': 'ask_tty'})],
    'rename': [F(classes=(R,), opts='-v -n --nono --verbose', must=(('-n', '--nono'),), ops='T P+', check='perl_subst',
                 says='show how {P} would be renamed, without renaming'),
               F(classes=(C,), opts='-v --verbose', ops='T P+', check='perl_subst', plan='rename_perl', says='rename {P} by {T}',
                 refused={'-f': 'overwrites', '--force': 'overwrites', '-e': 'perl_code', '-E': 'perl_code'})],
    # ---- destroy: rm goes to the bin (DELETE), which can be undone; the rest is refused ------------------------------------------
    'rm': [F(classes=(D,), opts='-r -R -f -d -v -i -I --recursive --force --dir --verbose --one-file-system --preserve-root --interactive=T',
             ops='P+', plan='bin', says='put {P} in the bin', refused={'--no-preserve-root': 'not_preserve_root'})],
    'rmdir': [F(classes=(D,), opts='-v --verbose --ignore-fail-on-non-empty', ops='P+', plan='bin', check='empty_dirs', says='put the empty folder {P} in the bin')],
    'shred': [F(classes=(D,), refuse='destroy')], 'dd': [F(classes=(D, ROOT), refuse='destroy')], 'mkfs': [F(classes=(D, ROOT), refuse='destroy')],
    'mke2fs': [F(classes=(D, ROOT), refuse='destroy')], 'mkswap': [F(classes=(D, ROOT), refuse='destroy')], 'wipefs': [F(classes=(D, ROOT), refuse='destroy')],
    'blkdiscard': [F(classes=(D, ROOT), refuse='destroy')], 'truncate': [F(classes=(D,), refuse='destroy')], 'srm': [F(classes=(D,), refuse='destroy')],
    'fdisk': [F(classes=(D, ROOT), refuse='root')], 'sfdisk': [F(classes=(D, ROOT), refuse='root')], 'gdisk': [F(classes=(D, ROOT), refuse='root')],
    'sgdisk': [F(classes=(D, ROOT), refuse='root')], 'parted': [F(classes=(D, ROOT), refuse='root')], 'cfdisk': [F(classes=(D, ROOT), refuse='root')],
}
# ---- root: the system door (KS3), refused here ----------------------------------------------------------------------------------
for _name in ('sudo', 'su', 'pkexec', 'doas', 'runuser', 'chown', 'chgrp', 'mount', 'umount', 'swapon', 'swapoff', 'shutdown', 'reboot', 'poweroff',
              'halt', 'init', 'telinit', 'service', 'update-rc.d', 'useradd', 'userdel', 'usermod', 'adduser', 'deluser', 'addgroup', 'delgroup',
              'groupadd', 'groupdel', 'passwd', 'chpasswd', 'visudo', 'modprobe', 'insmod', 'rmmod', 'update-grub', 'grub-install', 'ufw', 'iptables',
              'ip6tables', 'nft', 'hwclock', 'timedatectl', 'hostnamectl', 'localectl', 'chroot', 'aptitude', 'snap', 'flatpak', 'update-alternatives',
              'dpkg-reconfigure', 'apt-mark', 'apt-key', 'add-apt-repository', 'crontab', 'at', 'chattr', 'setcap', 'loginctl', 'setfacl'):
    TABLE.setdefault(_name, [F(classes=(ROOT,), refuse='root')])
PREFIXES = {'mkfs.': 'mkfs', 'fsck': 'mkfs'}      # mkfs.ext4 is mkfs; fsck.* repairs a disk (refused as mkfs is)

# ---- her dictionary: a request in plain words -> a known form (no model) ------------------------------------------------------
# Each entry: (the words, as a regular expression over the request in lower case, its punctuation and lead words taken off;
# the argv, where {x} is a word of the owner's taken by the expression's group x). The argv still goes through the classifier.
NAME = r'(?P<x>[a-z0-9][a-z0-9.+_@:-]{0,63})'
DICTIONARY = (
    (r'what(?: is|s) (?:using|taking|eating|filling) (?:up )?(?:all )?(?:of )?(?:my |the )?(?:disk|disc|drive|space|storage)(?: space)?(?: in my home)?',
     ['du', '-xh', '--max-depth=1', '~']),
    (r'(?:what|which folders?) (?:takes?|uses?) (?:up )?(?:the most )?(?:disk )?space in my home', ['du', '-xh', '--max-depth=1', '~']),
    (r'disk usage(?: of my home)?', ['du', '-xh', '--max-depth=1', '~']),
    (r'how full (?:is|are) (?:my |the )?(?:disks?|drives?|discs?)', ['df', '-h']),
    (r'(?:what is|whats|which ports are) listening(?: on (?:this computer|my computer|the network))?', ['ss', '-tuln']),
    (r'(?:open|listening) ports', ['ss', '-tuln']),
    (r'(?:my |the |open )?network connections', ['ss', '-tun']),
    (r'(?:my |the )?(?:default )?(?:routes?|gateway|routing table)', ['ip', 'route', 'show']),
    (r'(?:my )?(?:ip addresses|network interfaces|interfaces)', ['ip', '-br', 'address', 'show']),
    (r'(?:what is running|whats running|running (?:programs|processes)|list (?:the )?(?:programs|processes)|(?:my )?processes)',
     ['ps', '-eo', 'pid,user,pcpu,pmem,comm', '--sort=-pcpu']),
    (r'(?:top|top processes|busiest (?:programs|processes))', ['top', '-b', '-n', '1']),
    (r'(?:memory usage|free memory|how much memory is free|how much ram is free)', ['free', '-h']),
    (r'(?:uptime|how long has (?:it|this computer|the computer|my computer) been (?:up|on|running))', ['uptime', '-p']),
    (r'(?:which|what) kernel(?: version)?(?: is (?:this|running))?|kernel version', ['uname', '-r']),
    (r'(?:system|kernel) (?:name and )?(?:info|information)', ['uname', '-a']),
    (r'(?:cpu|processor) (?:info|information|details)|what processor(?: is this| do i have)?|which cpu(?: is this| do i have)?', ['lscpu']),
    (r'(?:my |the )?usb devices|whats plugged in by usb|what is plugged in by usb', ['lsusb']),
    (r'(?:my |the )?pci devices|(?:what|which) graphics card(?: is this| do i have)?|my graphics card', ['lspci']),
    (r'(?:the )?temperatures?|how hot is (?:it|the computer|my computer|the cpu)|(?:cpu|processor) temperature|fan speeds?', ['sensors']),
    (r'(?:my |the )?(?:disks and partitions|partitions|block devices)', ['lsblk', '-f']),
    (r'(?:what is mounted|whats mounted|mounted (?:drives|disks|file systems))', ['findmnt', '--real']),
    (r'(?:upgradable|upgradeable) packages|what can (?:i |be )?(?:upgrade|upgraded)|which packages can be upgraded', ['apt', 'list', '--upgradable']),
    (r'(?:failed services|which services failed|what services failed)', ['systemctl', 'list-units', '--state=failed', '--no-pager']),
    (r'(?:errors since boot|system errors|recent errors|errors in the (?:system )?log)', ['journalctl', '-b', '-p', 'err', '--no-pager', '-n', '50']),
    (r'(?:my log|my user log|my journal)', ['journalctl', '--user', '-b', '--no-pager', '-n', '50']),
    (r'(?:can i reach the internet|is the internet up|am i online|is the network up)', ['ping', '-c', '3', 'deb.debian.org']),
    (r'which package (?:has|owns|provides|installed) (?P<x>[a-z0-9/][a-z0-9/.+_@:-]{0,127})', ['dpkg', '-S', '{x}']),
    (r'what version of ' + NAME + r'(?: is installed| do i have)?', ['apt-cache', 'policy', '{x}']),
    (r'(?:where is|which) (?:the )?program ' + NAME, ['which', '-a', '{x}']),
    (r'is ' + NAME + r' running', ['pgrep', '-a', '{x}']),
    (r'(?:where is )?the manual (?:page )?(?:of|for) ' + NAME, ['man', '-w', '{x}']),
    (r'(?:the )?status of (?:the )?(?:service )?' + NAME, ['systemctl', 'status', '--no-pager', '{x}']),
    (r'(?:the )?files of (?:the )?package ' + NAME + '|what files did ' + NAME.replace('<x>', '<y>') + ' install', ['dpkg', '-L', '{x}']),
)
LEADS = ('please', 'kas', 'kasandra', 'can you', 'could you', 'show me', 'tell me', 'list', 'check', 'what are', 'i want to see', 'let me see')
# The Debian package that has a program, said when it is not on this computer (coreutils when not named).
PACKAGES = {'rename': 'rename', 'ss': 'iproute2', 'ip': 'iproute2', 'dig': 'bind9-dnsutils', 'host': 'bind9-host', 'ping': 'iputils-ping',
            'sensors': 'lm-sensors', 'lsusb': 'usbutils', 'lspci': 'pciutils', 'tree': 'tree', 'curl': 'curl', 'wget': 'wget', 'unzip': 'unzip',
            'zipinfo': 'unzip', 'xxd': 'xxd', 'hexdump': 'bsdextrautils', 'strings': 'binutils', 'man': 'man-db', 'rsync': 'rsync', 'file': 'file',
            'pgrep': 'procps', 'top': 'procps', 'ps': 'procps', 'free': 'procps', 'uptime': 'procps', 'sysctl': 'procps', 'lsmod': 'kmod',
            'whereis': 'util-linux', 'lsblk': 'util-linux', 'findmnt': 'util-linux', 'lscpu': 'util-linux', 'dmesg': 'util-linux',
            'rename.ul': 'util-linux', 'journalctl': 'systemd', 'systemctl': 'systemd', 'apt': 'apt', 'apt-get': 'apt', 'apt-cache': 'apt',
            'dpkg': 'dpkg', 'tar': 'tar', 'grep': 'grep', 'find': 'findutils', 'diff': 'diffutils', 'cmp': 'diffutils', 'which': 'debianutils',
            'hostname': 'hostname'}
