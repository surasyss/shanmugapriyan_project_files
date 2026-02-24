#! /bin/bash

# Shell Script to Cancel/Terminate AWS batch jobs in either runnable/running state
#
# Usage:
# $ ./bin/aws_batch_cancel_terminate.sh
# enter inputs based on the choices given
#

cancel_jobs(){
  echo "Canceling all the jobs in queue=webedi-batch-jobs & status=runnable"
  for i in $(aws batch list-jobs --job-queue webedi-batch-jobs --job-status runnable --output text --query jobSummaryList[*].[jobId])
  do
    echo "Cancel Job: $i"
    aws batch cancel-job --job-id $i --reason "Cancelling job."
    echo "Job $i canceled"
  done
}

terminate_jobs() {
  echo "Terminating all the jobs in queue=webedi-batch-jobs & status=running"
  for i in $(aws batch list-jobs --job-queue webedi-batch-jobs --job-status running --output text --query jobSummaryList[*].[jobId])
  do
    echo "Deleting Job: $i"
    aws batch terminate-job --job-id $i --reason "Terminating job."
    echo "Job $i deleted"
  done
}

take_action() {
  if [ "$1" == "1" ]
  then
    cancel_jobs
  elif [ "$1" == "2" ]
  then
    terminate_jobs
  else
    echo "Invalid input received: $1"
  fi
}

echo "AWS Batch Shell to Cancel/Terminate job"
read -p "Do you want to cancel/terminate runnable/running aws jobs? (y/n)" choice

if [ "$choice" == "y" ]
then
  echo "Enter the choice option:"
  echo -e "1. Cancel\n2. Terminate"
  read -p "Enter your choice: " action
  take_action "$action"
elif [ "$choice" == "n" ]
then
  echo "Safely sending you out of this shell"
else
  echo "Invalid input received: $choice"
fi
