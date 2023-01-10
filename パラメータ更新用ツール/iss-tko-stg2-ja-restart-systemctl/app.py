import boto3
import time
import config as cnf

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')


def __get_all_instance_ids(name:str) -> list:
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
    InstanceIds=instances,
    DocumentName="AWS-RunShellScript",
    Parameters = {"commands" : [command]}
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
  if all_instances[0]==cnf.Targets[2]:      #java-delayed
    return __send_command(all_instances[1], cnf.CommandList[2])
  else:                                     #cmn-api, indiv-api
    return __send_command(all_instances[1], cnf.CommandList[0])


def __server_status_for_each_type(all_instances):
  if all_instances[0]==cnf.Targets[2]:    #java-delayed
    return __send_command(all_instances[1], cnf.CommandList[3])
  else:                                   #cmn-api, indiv-api
    return __send_command(all_instances[1], cnf.CommandList[1])


def main():
  Instance_list = [ __get_all_instance_ids(instance) for instance in cnf.Targets ]

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


def lambda_handler(event, context):
  main()
