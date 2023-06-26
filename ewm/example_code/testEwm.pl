#!/usr/bin/perl
#
# Not all CMC RHEL7 machines have the requests module installed under the rh-python36
# software collection. gfwr610 for example does.
#
# --- We will have to get this resolved via Hai so this module exists on out pool
# machines.
#
# re error:  ModuleNotFoundError: No module named 'requests'
# To install, you should be able to do something like this (assuming you can write
# there)
#  source /opt/rh/rh-python36/enable
#  pip install requests
#
# pip will create this /opt/rh/rh-python36/root/usr/lib/python3.6/site-packages/requests
#  as well as some other stuff like urllib3
#
# 06/24/21 eggler created
#
use strict;
use JSON;




my $markerQueryName = "FSP marker lid EWM ids";

my $mySubscribedDefects = "Active STG Defects I Am Subscribed To";

my $ewmId = "284530"; # marker lid
   $ewmId = "284526"; # " "

my $cmd = "";
### set this to your own space if you like or use what is here. I don't guarantee
### how often this space will be updated
my $ewmRepoPath = "/afs/austin/projects/esw/bin/bld/ewmRepo";
$ewmRepoPath .= "/ewm";

# name of the query to run
my $query = $markerQueryName;

my $runqueryOut = $ENV{HOME} . "/runqueryOut.txt";
my $displayOut  = $ENV{HOME} . "/displayOut.txt";

my $whichEwm = "ewm_wrapper.py";  # can use ewm.py if running in a python3 env
                                  # my build machines are still all py2

# run the query, specifying an output file to hold the results
my $preParms = "--outfile $runqueryOut";
$cmd = "$ewmRepoPath/$whichEwm $preParms runquery \"$query\" "; 
print "$cmd\n";
system($cmd);

# run the display operation, putting output to a file
$preParms = "--outfile $displayOut";
$cmd = "$ewmRepoPath/$whichEwm $preParms display $ewmId ";
print "$cmd\n";
system($cmd);

print "Outputs are in $runqueryOut and $displayOut\n";


my $filename = "";
my $json_text = "";
my $json = "";
my $data = "";

#goto displayexample;

# Process the two different output files. Note that the json is converted
# to a complex data structure in perl.

print "\n----------------- Output from running a query and processing the result:\n";
$filename = $runqueryOut;

# decode the json
$json_text = do {
   open(my $json_fh, "<:encoding(UTF-8)", $filename)
      or die("Can't open \$filename\": $!\n");
   local $/;
   <$json_fh>
};

$json = JSON->new;
$data = $json->decode($json_text);

my $aref = $data->{results};

my $count = 0;
my $maxtoshow = 2;
for my $element (@$aref) {
    print "\nid:       $element->{Id}\n";
    print "  summary:  $element->{Summary}\n";
    print "  modified: $element->{'Modified Date'}\n";
    print "  status:   $element->{Status}\n";
    print "  owner:    $element->{'Owned By'}\n";
    print "  priority: $element->{Priority}\n";

    $count++;
    if ($count > $maxtoshow) { last; }
}

displayexample:

print "\n\n----------- Use the 'display' and work with the result\n";
# print out some of the values from the display operation
$filename = $displayOut;

$json_text = do {
   open(my $json_fh, "<:encoding(UTF-8)", $filename)
      or die("Can't open \$filename\": $!\n");
   local $/;
   <$json_fh>
};

$json = JSON->new;
my $ref_hashdata = $json->decode($json_text);

#for my $key (keys %{$ref_hashdata}) {
#     print "  $key  :   $ref_hashdata->{$key}\n";
#}
print "\nId : $ref_hashdata->{'Universal ID'}\n";
print "    Universal ID :   $ref_hashdata->{'Universal ID'}\n";
print "    Summary      :   $ref_hashdata->{Summary}\n";
print "    Severity     :   $ref_hashdata->{Severity}\n";
print "    State        :   $ref_hashdata->{State}\n";
print "    Status       :   $ref_hashdata->{Status}\n";
print "    Tags         :   $ref_hashdata->{Tags}\n";
print "    Priority     :   $ref_hashdata->{Priority}\n";
print "    Priority Justification :   $ref_hashdata->{'Priority Justification'}\n";



exit 0;



