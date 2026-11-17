import re, zipfile, sys, html
src, dst = sys.argv[1], sys.argv[2]
pat_f = re.compile(r'(<f[^>]*>)(.*?)(</f>)', re.S)
pat_ref = re.compile(r"(?<!['\w])(\d{2}_[0-9A-Za-z가-힣_]+)!")
n = 0
def fix(m):
    global n
    body, k = pat_ref.subn(r"'\1'!", m.group(2)); n += k
    return m.group(1) + body + m.group(3)
zin = zipfile.ZipFile(src); zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename.startswith('xl/worksheets/sheet') and item.filename.endswith('.xml'):
        data = pat_f.sub(fix, data.decode('utf-8')).encode('utf-8')
    zout.writestr(item, data)
zout.close(); print('quoted refs:', n)
