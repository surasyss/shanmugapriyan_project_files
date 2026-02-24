#!/bin/bash

if [ -f "/tmp/authorized_keys" ]; then
    cp /tmp/authorized_keys /home/ec2-user/.ssh/authorized_keys
else
    cp /home/ec2-user/.ssh/authorized_keys /tmp/authorized_keys
fi

users=$(aws iam get-group --group-name BeanstalkAccess | jq '.["Users"] | [.[].UserName]')
readarray -t users_array < <(jq -r '.[]' <<<"$users")
#declare -p users_array
for i in "${users_array[@]}"
do
        user_keys=$(aws iam list-ssh-public-keys --user-name $i)
        keys=$(echo $user_keys | jq '.["SSHPublicKeys"] | [.[].SSHPublicKeyId]')
        readarray -t keys_array < <(jq -r '.[]' <<<"$keys")
        for j in "${keys_array[@]}"
        do
                ssh_public_key=$(aws iam get-ssh-public-key --encoding SSH --user-name $i --ssh-public-key-id $j | jq '.["SSHPublicKey"] .SSHPublicKeyBody' | tr -d \")
                echo $ssh_public_key >> /home/ec2-user/.ssh/authorized_keys
        done
done
