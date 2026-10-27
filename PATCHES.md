# Changes from upstream

This is the Asciiverse packaging of [bastet](https://github.com/fph/bastet)
by Federico Poloni (GPL-3.0-or-later; the sources say "version 3 of the
License, or (at your option) any later version", LICENSE is the GPL 3).
Upstream is the `upstream` remote. The `asciiverse` branch starts from
upstream's `master` at `1b3e692` (2018-06-01), three commits after the
last release, 0.43.2 (2015-08-30); from 2017 and 2018, they move the
unordered_set header for newer Boost and stop scorer names from getting
a pair of quotes added each time the score file is written. fph.altervista.org/prog/bastet.html,
the old home page, lists 0.43.1 as the newest release and points to
GitHub for development. The version stays 0.43.2.

## Debian's patches

Debian's packaging repo (salsa.debian.org/games-team/bastet) is the
`debian` remote, fetched without its tags. Of the three patches in
Debian's 0.43.2-5:

- `format-security.patch` (Markus Koschany, 2021) is applied unchanged
  as its own commit, tagged `debian/0.43.2-5`: messages go to
  `mvwprintw()` through `"%s"`, so a high score name with a `%` in it is
  no longer read as a format string.
- `debian-bug-931550.patch` is upstream's `2cfeae7`, already in master.
- `revert_unordered_set.patch` undoes upstream's `0e03f8d` to go back to
  `<tr1/unordered_set>`; master's Boost header is kept instead.

Debian's other changes are packaging only (setgid binary, /var/games).

## Code

- **Builds with current compilers.** `std::bind2nd` (removed in C++17,
  which libc++ on macOS enforces) is a lambda, and the deprecated
  `boost::array::assign` is `fill`.
- **Keys and high scores in the player's data folder.** The high scores
  were looked for in `/var/games/bastet.scores2`, which needs a setgid
  binary, then `~/.bastetscores` with a notice on stderr each start; the
  keys were in `~/.bastetrc`, and a missing `HOME` crashed the game. Both
  are now `bastetrc` and `scores` in `$XDG_DATA_HOME/bastet`
  (`~/.local/share/bastet` when it is not set, `%APPDATA%\bastet` on
  Windows). Old `~/.bastetrc` and `~/.bastetscores` are read once if the
  new files do not exist yet.
- **No compiled Boost library.** The two files were read with
  Boost.Program_options, the only Boost part that is not header-only. A
  small `key = value` reader replaces it; the file format is unchanged,
  and names older versions wrapped in quotes are unwrapped. Only Boost's
  headers are needed to build.
- **Scores saved when they are made.** The files were written only when
  the program ended through its menu, so Ctrl+C lost every high score of
  the session, although README says earlier games are kept. They are
  saved after each new high score and after the keys are changed.
- **Keys through curses, with a timeout.** The falling block waited with
  `select()` on stdin, which misses keys curses has already buffered and
  does not exist for Windows consoles. It waits in `getch()` with
  `timeout()` until the next row is due, keeping a deadline so keys do
  not slow the fall (as `select()` did); a pause no longer counts against
  it. `usleep()` became `napms()`.
- **Enter drops the block.** The documented default for the hard drop,
  Enter, did nothing: the default was `KEY_ENTER`, which only the
  keypad's Enter sends, while the main Enter key arrives as `'\r'`. All
  three Enter codes count as one key now, in play and in the menus.
- **Centred, also after a resize.** The well was centred once with the
  next-block and score boxes hung off its right, and a resize was never
  handled; under 24 rows the first window failed and the game crashed.
  The well and boxes are centred together and placed again on
  `KEY_RESIZE` in play, the menus and the dialogs; the dialogs are
  centred exactly. The game needs 39x22: smaller is refused at start
  with a message, and a terminal made smaller while playing keeps the
  old windows, clipped, until it grows again.
- **No exceptions in the block chooser's search.** Each placement the
  search tried that ended the game threw `GameOver`, a few hundred
  throws per block near the end of a game. The visitors check the
  position first (the same test `Well::Lock` throws on), so the choices
  are unchanged. Under Wine, where throwing is slow, each of those blocks
  had taken seconds.
- **Windows.** `random()`/`srandom()` map to `rand()`/`srand()` there;
  nothing else was needed for MinGW and PDCurses.
- **Locale.** `setlocale()` before curses starts, so wide ncurses handles
  UTF-8 names in the high score table and draws the boxes with Unicode
  lines on terminals where it does not trust the VT100 line set (screen,
  tmux, the Linux console).
- The man page and INSTALL describe the new file places.

## Packaging (new files)

- `asciiverse/build.sh`: the eight sources in one compiler run against
  wide ncurses (PDCurses on Windows) and Boost's headers (`BOOST_INCLUDE`
  when the compiler does not find them).
- `asciiverse/package.sh`: one archive per target with the binary,
  `bastet.6`, LICENSE and README.
- `.github/workflows/release.yml`: static Linux in Alpine (x86_64,
  aarch64, Boost headers from `boost-dev`), macOS (x86_64, arm64, Boost
  headers from Homebrew) and Windows x86_64 (MinGW and PDCurses 3.9,
  Ubuntu's Boost headers), plus SHA256SUMS, on a tag.
- `asciiverse/record-preview.py`: records `asciiverse/bastet.cast`; a
  driver reads the well from the screen and places each block with a
  classic height, holes and bumpiness score, then fills the high score
  table and quits.

## Tested

Linux: native (glibc, ncursesw 6.6, Boost 1.90 headers) and static
(Alpine 3.22) builds; played at 80x24, 100x30 and 120x40, resized while
playing and in the menus, down to 30x15 and back; Enter, keypad Enter
and the pause; high scores written to the XDG folder and old
`~/.bastetscores` read, quoted names unwrapped. ASan and UBSan: 19
scripted games with random keys, pauses, resizes and high score entry,
no reports, exit 0. Windows: cross-built with MinGW-w64 against PDCurses
3.9 and run under Wine (a full game to the high score table, the name
saved in `%APPDATA%\bastet\scores`); arrow keys under Wine's console are
unchecked, as for nSnake. macOS: not built here.

## Ours

- **How to play it, at the top of README.** A short note on installing and
  starting it with av, or from a release archive; the original text follows
  unchanged.
