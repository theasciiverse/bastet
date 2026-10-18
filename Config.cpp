/*
    Bastet - tetris clone with embedded bastard block chooser
    (c) 2005-2009 Federico Poloni <f.polonithirtyseven@sns.it> minus 37

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "Config.hpp"

#include <boost/foreach.hpp>
#include <boost/format.hpp>
#include <curses.h>
#include <cassert>
#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <map>
#include <sys/stat.h>
#ifdef _WIN32
#include <direct.h>
#endif

using namespace std;
using namespace boost;

namespace Bastet{

  const size_t HowManyHighScores=10;
  const std::string RcFileName="bastetrc";
  const std::string HighScoresFileName="scores";
  //read once, when the new files do not exist yet
  const std::string LegacyRcFileName="/.bastetrc";
  const std::string LegacyHighScoresFileName="/.bastetscores";

  bool HighScores::Qualifies(int score){
    stable_sort(begin(),end());
    return begin()->Score < score;
  }

  int HighScores::InsertHighScore(int score, const std::string &scorer){
    if(!Qualifies(score)) return -1;
    HighScore hs={score,scorer};
    insert(begin(),hs); //we insert at the beginning to resolve ties
    stable_sort(begin(),end()); //the dumbest way to do it
    erase(begin());
    iterator it=find(begin(),end(),hs); //the dumbest way to find the position
    return end()-it+1;
  }

  Config config; //singleton instance

  static const char *Separator(){
#ifdef _WIN32
    return "\\";
#else
    return "/";
#endif
  }

  static void MakeDirs(const std::string &path){ //like mkdir -p
    for(size_t i=1;i<=path.size();++i){
      if(i==path.size() || path[i]=='/' || path[i]=='\\'){
	std::string part=path.substr(0,i);
#ifdef _WIN32
	if(part.size()==2 && part[1]==':') continue; //drive letter
	_mkdir(part.c_str());
#else
	mkdir(part.c_str(),0755);
#endif
      }
    }
  }

  ///the player's data folder: $XDG_DATA_HOME/bastet, else
  ///~/.local/share/bastet; %APPDATA%\bastet on Windows. Created if needed.
  static std::string DataDir(){
    static std::string result;
    if(!result.empty()) return result;
    std::string base;
#ifdef _WIN32
    const char *appdata=getenv("APPDATA");
    base=(appdata && *appdata) ? appdata : ".";
#else
    const char *xdg=getenv("XDG_DATA_HOME");
    const char *home=getenv("HOME");
    if(xdg && *xdg) base=xdg;
    else if(home && *home) base=std::string(home)+"/.local/share";
    else base=".";
#endif
    result=base+Separator()+"bastet";
    MakeDirs(result);
    return result;
  }

  static std::string Home(){
    const char *home=getenv("HOME");
    return (home && *home) ? home : "";
  }

  static std::string Trim(const std::string &s){
    size_t b=s.find_first_not_of(" \t\r\n");
    if(b==std::string::npos) return "";
    size_t e=s.find_last_not_of(" \t\r\n");
    return s.substr(b,e-b+1);
  }

  typedef std::map<std::string,std::string> Settings;

  ///reads "key = value" lines, '#' starts a comment line; the format
  ///Boost.Program_options wrote, so older files still read
  static bool ReadSettings(const std::string &fileName, Settings &out){
    ifstream ifs(fileName.c_str());
    if(ifs.fail()) return false;
    std::string line;
    while(getline(ifs,line)){
      line=Trim(line);
      if(line.empty() || line[0]=='#') continue;
      size_t eq=line.find('=');
      if(eq==std::string::npos) continue;
      out[Trim(line.substr(0,eq))]=Trim(line.substr(eq+1));
    }
    return true;
  }

  static int GetInt(const Settings &s, const std::string &key, int def){
    Settings::const_iterator it=s.find(key);
    if(it==s.end()) return def;
    char *end;
    errno=0;
    long v=strtol(it->second.c_str(),&end,10);
    if(end==it->second.c_str() || *end!='\0' || errno) return def;
    return int(v);
  }

  static std::string GetName(const Settings &s, const std::string &key, const std::string &def){
    Settings::const_iterator it=s.find(key);
    if(it==s.end()) return def;
    std::string v=it->second;
    //bastet 0.43.2 and older quoted names when writing but not when
    //reading, so names in old files may carry pairs of quotes
    while(v.size()>=2 && v[0]=='"' && v[v.size()-1]=='"')
      v=v.substr(1,v.size()-2);
    return v;
  }

  std::string Config::GetConfigFileName() const{
    return DataDir()+Separator()+RcFileName;
  }

  std::string Config::GetHighScoresFileName() const{
    return DataDir()+Separator()+HighScoresFileName;
  }

  Config::Config(){
    Settings options;
    if(!ReadSettings(GetConfigFileName(),options) && !Home().empty())
      ReadSettings(Home()+LegacyRcFileName,options);
    _keys.Down=GetInt(options,"Down",KEY_DOWN);
    _keys.Left=GetInt(options,"Left",KEY_LEFT);
    _keys.Right=GetInt(options,"Right",KEY_RIGHT);
    _keys.RotateCW=GetInt(options,"RotateCW",' ');
    _keys.RotateCCW=GetInt(options,"RotateCCW",KEY_UP);
    _keys.Drop=GetInt(options,"Drop",KEY_ENTER);
    _keys.Pause=GetInt(options,"Pause",'p');

    Settings highScores;
    if(!ReadSettings(GetHighScoresFileName(),highScores) && !Home().empty())
      ReadSettings(Home()+LegacyHighScoresFileName,highScores);
    boost::format scorer("Scorer%02d%02d");
    boost::format score("Score%02d%02d");
    for(int difficulty=0;difficulty<num_difficulties;difficulty++){
      for(size_t i=0;i<HowManyHighScores;++i)
	_hs[difficulty].push_back((HighScore){GetInt(highScores,str(score % difficulty % i),0),
	      GetName(highScores,str(scorer % difficulty % i),"No one played yet")});
      stable_sort(_hs[difficulty].begin(),_hs[difficulty].end()); //should not be needed but...
    }
  }

  Keys *Config::GetKeys(){
    return &_keys;
  }

  HighScores *Config::GetHighScores(int difficulty){
    assert(difficulty>=0 && difficulty<num_difficulties);
    return &(_hs[difficulty]);
  }

  void Config::Save(){
    ofstream ofs(GetConfigFileName().c_str());
    ofs<<"# Automatically regenerated by the program at each run, edit at your own risk\n";
    ofs<<"Down = "<<_keys.Down<<"\n";
    ofs<<"Drop = "<<_keys.Drop<<"\n";
    ofs<<"Left = "<<_keys.Left<<"\n";
    ofs<<"Pause = "<<_keys.Pause<<"\n";
    ofs<<"Right = "<<_keys.Right<<"\n";
    ofs<<"RotateCCW = "<<_keys.RotateCCW<<"\n";
    ofs<<"RotateCW = "<<_keys.RotateCW<<"\n";
    ofs.close();

    ofstream ofs2(GetHighScoresFileName().c_str());
    ofs2<<"# Do not edit this file, Bastet sees you\n";
    boost::format scorer("Scorer%02d%02d");
    boost::format score("Score%02d%02d");
    for(int difficulty=0;difficulty<num_difficulties;++difficulty){
      int i=0;
      BOOST_FOREACH(const HighScore &hs, _hs[difficulty]){
	ofs2<<str(scorer % difficulty % i) << " = " << hs.Scorer << "\n";
	ofs2<<str(score % difficulty % i) << " = " << hs.Score <<"\n";
	i++;
      }
    }
  }

  Config::~Config(){
    Save();
  }
}
