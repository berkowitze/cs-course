echo "[]" >> ../hta/grading/extensions.json
echo "{}" >> ../hta/s-t-blocklist.json
echo "{}" >> ../ta/t-s-blocklist.json

echo '{
  "aa_README": [
    "all keys must be the same as the Google Form dropdown option",
    "dates are mm/dd/yyyy HH:MM_M format (i.e. 11/29/2018 05:00PM)",
    "format for each assignment in custom_types.py"
  ],
  "assignments": {}
}' >> ../ta/newasgn.json

echo "" >> ../hta/handin/submission_log.txt
