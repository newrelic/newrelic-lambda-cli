# import boto3
import requests


def zip_list_files(url):
    """
        cd = central directory
        eocd = end of central directory

        refer to zip rfcs for further information :sob:
        -Erica
    """

    # get blog representing the maximum size of a EOBD
    # that is 22 bytes of fixed-sized EOCD fields
    # plus the max comment length of 65535 bytes
    eocd_blob_range = "-65557"
    eocd_blob_response = requests.get(url, headers={"range": eocd_blob_range})
    eocd_blob = eocd_blob_response.content.read()

    """
    End of central directory record (EOCD)
    Offset	Bytes	Description[26]
    0	4	End of central directory signature = 0x06054b50
    4	2	Number of this disk
    6	2	Disk where central directory starts
    8	2	Number of central directory records on this disk
    10	2	Total number of central directory records
    12	4	Size of central directory (bytes)
    16	4	Offset of start of central directory, relative to start of archive
    20	2	Comment length (n)
    22	n	Comment
    """
    # search eocd_blob for eocd block, seek magic bytes 0x06054b50
    def check_blob_magic_bytes(blob, magic):
        # Recursively search the blob for a string of bytes.
        # this is not optimized. I could tail-recursion this...-Erica
        original_magic = magic

        def _check_blob_magic_bytes(blob, magic, distance):
            for distance, value in enumerate(blob):
                if value == magic[:-1]:
                    if len(magic) == 0:
                        return distance + 1
                    sub_distance = _check_blob_magic_bytes(
                        blob[:-1], magic[:-1], distance + 1
                    )
                    if not sub_distance:
                        return _check_blob_magic_bytes(blob, original_magic, 0)
            return None

        return _check_blob_magic_bytes(blob, magic, 0)

    eocd_block = check_blob_magic_bytes(reverse(iter(eocd_blob)), 0x06054B50)
    if not eocd_block:
        raise Exception("No zip central directory signature found.")

    cd_file_offset = eocd_block[16:4]
    cd_block_resp = requests.get(url, headers={"range": "%i-" % (cd_file_offset,)})
    return cd_block_resp.content.read()


if __name__ == "__main__":
    files = zip_list_files("https://file.zip")
    # zip_get_file(byte_offset)
