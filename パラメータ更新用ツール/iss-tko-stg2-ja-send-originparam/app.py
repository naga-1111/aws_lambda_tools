import boto3
import time
import config as cnf

ssm = boto3.client('ssm')


def __get_parameters(param_keys:list) -> list:
  res = ssm.get_parameters(
    Names=param_keys,
    WithDecryption=True
  )
  return res["Parameters"]


def __put_parameter(param_key:str, value:str) -> list:
  res = ssm.put_parameter(
    Name=param_key,
    Value=value,
    Overwrite=True
  )
  return res


def main():
  res = [__put_parameter(i[0], i[1]) for i in cnf.origin_params]
  time.sleep(1)
  keys = [i[0] for i in cnf.origin_params]
  param = __get_parameters(keys)
  [print(f'{i["Name"]}  :  {i["Value"]}') for i in param]
  return


def lambda_handler(event, context):
  main()
