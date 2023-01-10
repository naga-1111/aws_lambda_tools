import boto3
import time

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
##########
#ssm = boto3.client('ssm')    #lambdaには権限を与えるからこれだけでいい


TestParams = [
  ["/iss/tko/stg2/env/JCP", "apple"],
]


def __get_parameters(param_keys:list) -> list:
  """パラメータストア参照
    Args:
      param_key:str パラメータ名
  """
  res = ssm.get_parameters(
    Names=param_keys,
    WithDecryption=True
  )
  return res["Parameters"]


def __put_parameter(param_key:str, value:str) -> list:
  """パラメータストア更新
    Args:
      param_key:str パラメータ名
      value:str パラメータ値
  """
  res = ssm.put_parameter(
    Name=param_key,
    Value=value,
    Overwrite=True
  )
  return res

def main():
  res = [__put_parameter(i[0], i[1]) for i in TestParams]
  time.sleep(1)
  keys = [i[0] for i in TestParams]
  param = __get_parameters(keys)
  [print(f'{i["Name"]}  :  {i["Value"]}') for i in param]
  return

if __name__ == "__main__":
#def lambda_handler(event, context):
  main()
