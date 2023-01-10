
AWSEnv = "stg2"

Targets = [
  f"iss-tko-{AWSEnv}-i-cmn-api",        #api
  f"iss-tko-{AWSEnv}-i-indiv-api",      #api
  f"iss-tko-{AWSEnv}-i-java-delayed"    #java
]

CommandList = [
  "/usr/bin/systemctl restart app-api",          #0
  "/usr/bin/systemctl status app-api",           #1
  "/usr/bin/systemctl restart app-javadelayed",  #2
  "/usr/bin/systemctl status app-javadelayed"    #3
]
