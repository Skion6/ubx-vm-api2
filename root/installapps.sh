#!/bin/bash
set -e

json_file="/options.json"

if jq ".defaultapps | contains([0])" "$json_file" | grep -q true; then
    chmod +x /installable-apps/wine.sh
    /installable-apps/wine.sh
fi
if jq ".defaultapps | contains([1])" "$json_file" | grep -q true; then
    chmod +x /installable-apps/helium.sh
    /installable-apps/helium.sh
fi
if jq ".defaultapps | contains([2])" "$json_file" | grep -q true; then
    chmod +x /installable-apps/xarchiver.sh
    /installable-apps/xarchiver.sh
fi
if jq ".apps | contains([2])" "$json_file" | grep -q true; then
    chmod +x /installable-apps/synaptic.sh
    /installable-apps/synaptic.sh
fi
if jq ".apps | contains([3])" "$json_file" | grep -q true; then
    chmod +x /installable-apps/aqemu.sh
    /installable-apps/aqemu.sh
fi

# clean stuff

rm -rf /installable-apps
