import socket
import os
import threading
import multiprocessing
import sys
port = 80
#Dau hieu phan tach phan header va body
header_delimiter = b"\r\n\r\n"
#Tham so de get content-length
content_length_field = b'Content-Length:'
# tách host và path khỏi url
def split_URL(URL):
    #Truong hop co http://
    if (URL.find('http://')!=-1):
        pos_begin=len('http://')
        if URL.find('/',len('http://'))!=-1:
            pos_end=URL.find('/',len('http://'))
            host=URL[pos_begin:pos_end]
            path=URL[pos_end+1:]
        else:
            host=URL[pos_begin:]
            path=''
        return (host, path)
    #Truong hop khong co http://
    else:
        pos_end=URL.find('/')
        host=URL[0:pos_end]
        path=URL[pos_end+1:]
        return (host,path)
#Ham dinh dang request tu host va path
def formatted_http_request(host, path):
     request ="GET /" + path + " HTTP/1.1\r\nHost: " + host + "\r\nConnection: keep-alive\r\n\r\n"
     return request.encode()
# kết nối đến server và gửi request
def connect_to_web_server(URL):
     client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     host,path=split_URL(URL)
     host_name=socket.gethostbyname(host)
     try:
        client.connect((host_name,port))
        request = formatted_http_request(host, path)
        client.send(request)
        return client
     except: print("Can't connect to web server!!!!")

#ham tra ve header
def getHeader(client):
    header = b""
    chunk = b""
    # lấy từng byte 1 đến hết body
    while header_delimiter not in header:
        chunk = client.recv(1)
        header += chunk
    return header

# ham tra ve location 
def handleHeader (header):
    location = b''
    for line in header.split('\r\n'):
        if b'Location:'in line:
            location = line[line.find(' '):]
        
    return location
# ham lay contentlength
def get_content_length(header):
       for line in header.split(b'\r\n'):
           if content_length_field in line:
                return int(line[len(content_length_field):])
       #Truong hop response dang tranfer-encoding:chunked (khong ton tai content-length)
       return 0

#Ham nhan du lieu dang content-length
def getData(client, content_length):
    data = b""
    byte_received = 0

    while byte_received != content_length:
        data += client.recv(content_length - byte_received)
        byte_received = len(data)
    return data

#ham tra ve phan body duoc nhan duoi dang content-length
def get_data_by_content_length(client, header):
    content_length = get_content_length(header)
    return getData(client,content_length)

#ham dinh dang ten file can tai ve
def get_Format_Name_File_Download(host,path):
    if(path=='' ):
        return host+'_index.html'
    else:
       path_arr=path.split('/')
       return host+'_'+path_arr[-1]

# hàm download 1 file duy nhất
def download_Only_file(URL, file_name):
    client =connect_to_web_server(URL)
    header =getHeader(client)
    if b'HTTP/1.1 200' not in header:
        print("Can't connect to server: ")
        return False
    data_received = get_data_by_content_length(client, header)

    with open(file_name, 'wb') as f:
         f.write(data_received)
    f.close()
    client.close()

#Down_file theo kieu transfer-encoding

#Ham kiem tra du lieu tra ve co phai kieu chunked hay khong
def is_transfer_encoding_chunked(header):
    if header.find(b'Transfer-Encoding: chunked')==-1:
        return False
    else:
        return True
# Ham lay do dai cua chunked
def get_chunk_size(client):
    size_str = client.recv(2)
    while size_str[-2:] != b"\r\n":
        size_str += client.recv(1)
    return int(size_str[:-2], 16)

#Ham lay du lieu kieu chunked
def get_chunk_data(client,chunk_size):
    data = client.recv(chunk_size)
    client.recv(2)
    return data

#Ham tra ve phan body duoc nhan duoi dang chunked
def get_body_type_chunked(client,header):
   respbody =b''
   while True:
        chunk_size = get_chunk_size(client)
        if (chunk_size == 0):
           break
        else:
           chunk_data = get_chunk_data(client,chunk_size)
           respbody += chunk_data
   return respbody

#Ham download_file kieu chunked
def download_Only_file_Con_or_chunked(file_name,body):
    with open(file_name, 'wb') as f:
        f.write(body)
    f.close()



#FOLDER
#Ham kiem tra xem URl co phai la URL dung de tai folder hay khong
def isFolder(Path):
    if Path == "": return False
    if Path[len(Path)-1] == '/':
        return True
    return False

#Ham tao tao ten folder tu host va path
def get_name_folder(host,path):
    path_arr=path.split('/')
    if(path_arr[-1]!=''): return host+'_'+path_arr[-1]
    else:return host+'_'+path_arr[-2]

#Ham tao list ten cac file trong folder can tai ve
def Crete_namefile_in_forder(body):
    sub_file = []
    data_str = body.decode()
    check = data_str.split('</td></tr>')
    for line in check:
        if (line.find('a href') != -1):
            pos_start = line.find('a href') + 8
            pos_end = line.find('">', pos_start)
            file_name = line[pos_start:pos_end]
            if (file_name.find('.') != -1):
                sub_file.append(file_name)
    return sub_file

# tạo 1 luồng request
def handleSever(URL, folder_name):
    host,path = split_URL(URL)
    file_name = folder_name + "\\" +get_name_folder(host,path)
    download_Only_file(URL,file_name)

#Ham tai xuong cac file trong folder da tao
def download_forder(URL,folder_name,body):
    #List cac ten file trong folder
    thread=Crete_namefile_in_forder(body)
    for i in range(len(thread)):
       process = threading.Thread(target=handleSever, args=(URL+thread[i], folder_name))
       process.start()

#Ham tai du lieu tu mot url bat ki
def Download(URL):
    host,path=split_URL(URL)
    client = connect_to_web_server(URL)
    header = getHeader(client)
    #Neu khong ket noi duoc hoac ket noi duoc nhung khong tim thay trang
#    if b'HTTP/1.1 200' not in header:
#        print("Can't connect to server: ")
#        return False
    #Neu header tra ve la moved parmantently
    if b'HTTP/1.1 301' in header:
        # moved parmantently
        # điều hướng tới địa chỉ mới
        URL = handleHeader(header)
        # connect lại với server mới
        Download(URL)
        return True
        # =>download file
    elif b'HTTP/1.1 404' in header:
        print("Not Found!! ")
        return False
    elif b'HTTP/1.1 401' in header:
        print("Not support!!")
    elif b'HTTP/1.1 200' in header:                                                                                         
        if(is_transfer_encoding_chunked(header)):
            body=get_body_type_chunked(client,header)
        else :
            body=get_data_by_content_length(client,header)
        if(isFolder(path)==False):
            file_name=get_Format_Name_File_Download(host,path)
            download_Only_file_Con_or_chunked(file_name,body)
        else:
            folder_name=get_name_folder(host,path)
            os.mkdir(folder_name)
            download_forder(URL,folder_name,body)
    client.close()
    return True
# kết nối đến nhiều sever cùng lúc
def downloadListURLs(list_urls):
#    for i in range(len(list_urls)):
#        thread = threading.Thread(target=Download, args= {list_urls[i]})
#        thread.start()
    for i in range(len(list_urls)):
        p = multiprocessing.Process(target = Download, args = {list_urls[i]})
        p.start()
        p.join()


#Ham main
def main():
    list_url=['http://web.stanford.edu/class/cs231a/project.htm']
    downloadListURLs(list_url)
if __name__ == '__main__':
    main()




