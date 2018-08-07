# this file is run every minute by a cron daemon on eberkowi
# account on melissa host computer (TA lab)
# this really needs to be updated to do chgrp things
chmod -R 770 /course/cs0111/hta/ &>> /course/cs0111/hta/permission_errors.log
chmod -R 770 /course/cs0111/ta/ &>> /course/cs0111/hta/permission_errors.log
chmod -R 770 /course/cs0111/tabin/ &>> /course/cs0111/hta/permission_errors.log
chmod -R 770 /course/cs0111/htabin/ &>> /course/cs0111/hta/permission_errors.log
