#!/bin/bash

export > /home/ec2-user/run_bash.sh

echo "cmd=\$@" >> /home/ec2-user/run_bash.sh
echo -e "if [ ! \$cmd ];then \ncmd='/bin/bash' \nfi">> /home/ec2-user/run_bash.sh
echo "sudo docker run -it -e ENV_CONFIG=\${ENV_CONFIG} aws_beanstalk/current-app \${cmd}" >> /home/ec2-user/run_bash.sh
chmod +x /home/ec2-user/run_bash.sh
