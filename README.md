# File Uploader
The file uploader is written in the Python programming language using FastAPI. All uploaded files are stored on the server. The API provides the ability for both previewing and downloading files, depending on the file extension.<br>

## API Documentation
Currently, the API is hosted at the URL [fu.andcool.ru](https://fu.andcool.ru/). Page redirection is performed using an nginx proxy server.
<br>
The API has two endpoint URLs:<br>
- `/file/` — endpoint where all files are located<br>
- `/api/upload/` — endpoint to which requests for file upload are sent<br>

`GET https://fu.andcool.ru/file/<key>` — Retrieves a file based on the key.<br>
Successful execution will return a `200` status code along with the binary file and the specified `Content-Type`. If the file type cannot be determined, the API returns the file in download mode.<br>

### Possible Errors
| Error Code | Description                        | Possible Causes                              |
|------------|------------------------------------|----------------------------------------------|
| 404        | File not found                     | The file referenced by the key does not exist|


`POST https://fu.andcool.ru/api/upload/` — Uploads a file to the server.<br>
The request body should contain the file object. Only one file is allowed, and its size must not exceed 100MB.<br>
Maximum request frequency: **Once per minute**<br>

### Example Request
```
{
    "file": <file object>
}
```

### Example Response
Upon successful execution, the API will return a `200` status code and a JSON response.<br>
```
{
    "status": "success",                // Request status
    "message": "File uploaded successfully",  // Message
    "file_url": "4yn-8yjhsu"            // Unique file key
}
```

| Error Code | Description                          | Possible Causes                            |
|------------|--------------------------------------|--------------------------------------------|
| 400        | No file uploaded                     | No file is present in the request body     |
| 400        | Bad file extension                   | The file does not have an extension        |
| 413        | File size exceeds the limit (100MB)   | File size exceeds 100MB                     |
