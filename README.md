# File Uploader
The file uploader is implemented in the Python programming language using FastAPI. All uploaded files are stored on the server. The API supports both file preview and download functionalities, depending on the file extension.

## API Documentation
Currently, the API is hosted at [fu.andcool.ru](https://fu.andcool.ru/). Page redirection is handled through the nginx proxy server. The API has three endpoint URLs:
- `/file/` — endpoint where all files are located
- `/api/upload` — endpoint for receiving file upload requests
- `/api/delete/` — endpoint for deleting files

### File Retrieval
`GET https://fu.andcool.ru/file/<file_url>` — Retrieves a file based on the provided URL.
Successful execution returns a `200` status code along with the binary file and the specified `Content-Type`. If the file type cannot be determined, the API returns the file in download mode.

#### Possible Errors
| Error Code | Description                  | Possible Reasons                           |
|------------|------------------------------|--------------------------------------------|
| 404        | File not found               | The file referenced by the code does not exist |

### File Upload
`POST https://fu.andcool.ru/api/upload?include_ext=false` — Uploads a file to the server.
The request body should contain the file to be uploaded. Only one file is allowed, and its size should not exceed 100MB.
The query parameter `include_ext` can be set to `true/false` to indicate whether the file extension should be included in the file URL.
The maximum request frequency is **2/minute**.

#### Response Example
Upon successful execution, the API returns a `200` status code along with a JSON response.
```json
{
    "status": "success",
    "message": "File uploaded successfully",
    "file_url": "4yn-8yjhsu",
    "file_url_full": "https://fu.andcool.ru/file/4yn-8yjhsu",
    "key": "6b9a1c1b-5594-4cb9-8d49-99a4c28782a1",
    "ext": ".mp4",
    "user_filename": "test.mp4"
}
```

#### Possible Errors
| Error Code | Description                           | Possible Reasons                           |
|------------|---------------------------------------|--------------------------------------------|
| 204        | No file uploaded                      | No file is present in the request body     |
| 400        | Bad file extension                    | The file does not have an extension        |
| 413        | File size exceeds the limit (100MB)   | The file size exceeds 100MB                |

### File Deletion
`DELETE https://fu.andcool.ru/api/delete/<file_url>?key=<unique key>` — Deletes a file.
Successful execution returns a `200` status code, removing the file from the server.

#### Possible Errors
| Error Code | Description                   | Possible Reasons                       |
|------------|-------------------------------|----------------------------------------|
| 404        | File not found                | The file for deletion is not found     |
| 400        | Invalid unique key            | The provided unique key is invalid     |
