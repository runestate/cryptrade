prefix='^.+'
postfix='.+\]|$'
color_red='01;31'
awk '{ 
      gsub("^.+(TRACE).+",   "\033[2;49m&\03"); 
		  gsub("^.+DEBUG.+?]",    "\033[0;34m&\033[0m");
      gsub("^.+INFO.+]",     "\033[0;36m&\033[0m"); 
      gsub("^.+WARN.+]",     "\033[1;33m&\033[0m"); 
      gsub("^.+ERROR.+]",    "\033[0;31m&\033[0m"); 
      gsub("^.+CRITICAL.+]", "\033[1;31m&\033[0m"); 
      gsub("\".+\", line [0-9]+",    "\033[0;37m&\033[0m"); 
      gsub("^.+Error($|:.+)", "\033[0;31m&\033[0m"); 
      gsub("^Exception: .+", "\033[0;31m&\033[0m"); 
      print 
  }'
