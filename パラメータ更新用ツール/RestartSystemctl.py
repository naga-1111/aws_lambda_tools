import boto3
import time

# ローカル開発用スクリプト
# lambda用にzipファイルにするときはファイル名をapp.py
# def lambda_handler(event, context):内の関数がメイン処理
# になるようにする

########ローカル開発用のセッション、lambdaに実装するときは全部消す
import botocore.session
from botocore import credentials
import os
cli_cache = os.path.join(os.path.expanduser('~'), '.aws/cli/cache')
botocore_session = botocore.session.Session(profile='stg2')
botocore_session.get_component('credential_provider') \
    .get_provider('assume-role').cache = credentials.JSONFileCache(cli_cache)
session = boto3.session.Session(botocore_session=botocore_session)
ssm = session.client('ssm')
ec2 = session.client('ec2')
##########
#ec2 = boto3.client('ec2')    #lambdaには権限を与えるからこれだけでいい
#ssm = boto3.client('ssm')

Targets = [
  "iss-tko-stg2-i-cmn-api",
  "iss-tko-stg2-i-indiv-api",
  "iss-tko-stg2-i-java-delayed"
]

CommanList = [
  "/usr/bin/systemctl restart app-api",          #0
  "/usr/bin/systemctl status app-api",           #1
  "/usr/bin/systemctl restart app-javadelayed",  #2
  "/usr/bin/systemctl status app-javadelayed"    #3
]



def __get_all_instance_ids(name:str) -> list:
  """全インスタンスid取得
    Args:
      name:str インスタンス名
  """
  response = ec2.describe_instances(
    Filters=[
      {
          'Name':'tag:Name',
          'Values':[name],
      },
      {
          'Name':'instance-state-name',
          'Values':['running']
      }])
  instance_id_list = [i["Instances"][0]["InstanceId"] for i in response['Reservations']]
  return [name, instance_id_list]


def __send_command(instances:list, command:str):
  res = ssm.send_command(
    InstanceIds=instances,                  #list
    DocumentName="AWS-RunShellScript",
    Parameters = {"commands" : [command]}   #"/usr/bin/systemctl status app-api"
  )
  return res


def __get_command_status(command_id):
  res = ssm.list_command_invocations(
    CommandId=command_id,
    Details=True
  )
  print(res["CommandInvocations"][0]['CommandPlugins'][0]["Output"])
  print("\n\n====\n\n")
  return


def __restart_server_for_each_type(all_instances):
  if all_instances[0]=='iss-tko-stg2-i-java-delayed':
    return __send_command(all_instances[1], CommanList[2])
  else:
    return __send_command(all_instances[1], CommanList[0])


def __server_status_for_each_type(all_instances):
  if all_instances[0]=='iss-tko-stg2-i-java-delayed':
    return __send_command(all_instances[1], CommanList[3])
  else:
    return __send_command(all_instances[1], CommanList[1])

def main():
  Instance_list = [ __get_all_instance_ids(instance) for instance in Targets ]

  print("restart instances...")
  [__restart_server_for_each_type(i) for i in Instance_list]
  time.sleep(30)
  print("done")


  print("check server status...")
  res = [__server_status_for_each_type(i) for i in Instance_list]
  time.sleep(10)


  [__get_command_status(i["Command"]["CommandId"]) for i in res]
  print("\n====complete===\n")
  return

if __name__ == "__main__":
#def lambda_handler(event, context):
  main()
