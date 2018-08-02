# this file is run every minute by a cron daemon on eberkowi
# account on melissa host computer (TA lab)
# this really needs to be updated to do chgrp things
chmod -R 770 /course/cs0050/hta/ &>> /course/cs0050/hta/permission_errors.log
chmod -R 770 /course/cs0050/ta/ &>> /course/cs0050/hta/permission_errors.log
chmod -R 770 /course/cs0050/tabin/ &>> /course/cs0050/hta/permission_errors.log
chmod -R 770 /course/cs0050/htabin/ &>> /course/cs0050/hta/permission_errors.log
