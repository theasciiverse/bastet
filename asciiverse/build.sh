#!/bin/sh
# Builds bastet into out/: the eight sources in one compiler run (one
# process, so no parallel jobs to limit). The compiler, flags and curses
# library come from the environment, so one script serves every target
# (see .github/workflows/release.yml):
#
#   asciiverse/build.sh                                       # Linux
#   LDFLAGS="-static -s" asciiverse/build.sh                  # Alpine, static
#   CURSES_LIBS=-lncurses BOOST_INCLUDE=/opt/homebrew/include \
#     CXXFLAGS="-O2 -arch arm64" asciiverse/build.sh          # macOS
#   CXX=x86_64-w64-mingw32-g++ PDCURSES=/path/to/PDCurses-3.9 \
#     BOOST_INCLUDE=/path/with/boost EXE=.exe LDFLAGS="-static -s" \
#     asciiverse/build.sh                                     # Windows
#
# Only Boost's headers are used (PATCHES.md); BOOST_INCLUDE names the
# folder holding boost/ when the compiler does not look there itself.
set -eu
cd "$(dirname "$0")/.."
CXX="${CXX:-c++}"
EXE="${EXE:-}"
CXXFLAGS="${CXXFLAGS:--O2}"
LDFLAGS="${LDFLAGS:-}"
CURSES_LIBS="${CURSES_LIBS:--lncursesw}"
SOURCES="Ui.cpp Block.cpp Well.cpp BlockPosition.cpp Config.cpp BlockChooser.cpp BastetBlockChooser.cpp main.cpp"
INCLUDES=""
if [ -n "${BOOST_INCLUDE:-}" ]; then INCLUDES="-I$BOOST_INCLUDE"; fi
if [ -n "${PDCURSES:-}" ]; then
  INCLUDES="$INCLUDES -I$PDCURSES"
  CURSES_LIBS="$PDCURSES/wincon/pdcurses.a"
fi
mkdir -p out
rm -f "out/bastet$EXE"
# shellcheck disable=SC2086
nice -n 10 $CXX -std=c++11 -DNDEBUG -Wall $CXXFLAGS $INCLUDES -o "out/bastet$EXE" \
  $SOURCES $CURSES_LIBS $LDFLAGS
cp bastet.6 out/bastet.6
echo "built bastet$EXE"
