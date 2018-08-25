# this file is run every minute by a cron daemon on eberkowi
# account on melissa host computer (TA lab)
# this really needs to be updated to do chgrp things
#chmod -R 770 /course/cs0111/hta/ &>> /course/cs0111/hta/permission_errors.log
#chmod -R 770 /course/cs0111/ta/ &>> /course/cs0111/hta/permission_errors.log
#chmod -R 770 /course/cs0111/tabin/ &>> /course/cs0111/hta/permission_errors.log
#chmod -R 770 /course/cs0111/htabin/ &>> /course/cs0111/hta/permission_errors.log
BASE="/course/cs0111"
TAG="$BASE/ta/grading"

cd $TAG

# give TAs r/w access to grading folder...
chgrp -R cs-0111ta $TAG
chmod 770 $TAG

# ... except certain files that they only get rx access to
cat $TAG/rxonly.txt | xargs chgrp cs-0111hta
cat $TAG/rxonly.txt | xargs chmod 770 
cat $TAG/rxonly.txt | xargs setfacl -m g:cs-0111ta:rx

