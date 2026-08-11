NUM_DISKS=$1

if [[ $# -ne 1 ]] ; then
    echo 'single input argument required'
    exit 1
fi

for ((i = 0; i < NUM_DISKS; i++)); do
	dd if=/dev/zero bs=512 of="disk$i.bin" iflag=fullblock count=4096 # 2MB file
done

echo "$NUM_DISKS disks created"

