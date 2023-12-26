# File Uploader
The file uploader is developed in the Python programming language using FastAPI. All uploaded files are stored on the server. The API provides functionalities for both file preview and file download, depending on the file extension.

## API Documentation
Currently, the API is hosted at [fu.andcool.ru](https://fu.andcool.ru/). Page redirection is handled through the nginx proxy server. The API consists of three endpoint URLs:
- `/file/` — endpoint where all files are located
- `/api/upload` — endpoint for receiving file upload requests
- `/api/delete/` — endpoint for deleting files

### 1.1 Authorization Errors
In all requests where the `Authorization` header is sent, there are errors related to authorization problems. The `Authorization` header should have the format `Authorization: Bearer <token>`.

#### Response Example
All errors of this type have a consistent response format and always return an HTTP code of `400`. In the documentation, this section will be referred to as `1.1`.
```
{
    "status": "error",
    "auth_error": {
        "message": "error message",
        "errorId": <error code>
    }
}
```
List of errors:
| errorId    | message                                                | Reasons                                           |
|------------|--------------------------------------------------------|---------------------------------------------------|
| -1         | No Authorization header provided                       | The request is missing the `Authorization` header |
| -2         | Authorization header must have `Bearer <token>` format | The `Authorization` header has an incorrect format |
| -3         | Access token expired                                   | The token has expired                             |
| -4         | Invalid access token                                   | The token cannot be decrypted                     |
| -5         | Token not found                                        | The token is not found                            |

### 1.2 Basic API
`GET https://fu.andcool.ru/file/<file_url>` — Retrieves a file based on the URL.
Successful execution returns a `200` status code along with the binary file and the specified `Content-Type`. If the file type cannot be determined, the API returns the file in download mode.

#### Possible Errors
| Error Code | Description                  | Possible Reasons                           |
|------------|------------------------------|--------------------------------------------|
| 404        | File not found               | The file referenced by the code does not exist |

`POST https://fu.andcool.ru/api/upload?include_ext=false` — Uploads a file to the server.
The request body should contain the file to be uploaded. Only one file is allowed, and its size should not exceed 100MB.
The query parameter `include_ext` can be set to `true/false` to indicate whether the file extension should be included in the file URL.
The maximum request frequency is **twice per minute**.
The request can also include the `Authorization` header, containing the user's unique token.
If the token is not provided or is not valid, the `synced` field in the response body will be set to `false`. The file will be uploaded to the server regardless of whether the `Authorization` header is included in the request. The `auth_error` field in the response body contains the authentication error (section `1.1`), and if there is no error, the field will be `{}`.

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
    "user_filename": "test.mp4",
    "synced": true,
    "auth_error": {}
}
```

#### Possible Errors
| Error Code | Description                           | Possible Reasons                           |
|------------|---------------------------------------|--------------------------------------------|
| 204        | No file uploaded                      | No file is present in the request body     |
| 400        | Bad file extension                    | The file does not have an extension        |
| 413        | File size exceeds the limit (100MB)    | The file size exceeds 100MB                 |

`DELETE https://fu.andcool.ru/api/delete/<file_url>?key=<unique key>` — Deletes a file.
Successful execution returns a `200` status code, removing the file from the server.

#### Possible Errors
| Error Code | Description                   | Possible Reasons                       |
|------------|-------------------------------|----------------------------------------|
| 404        | File not found                | The file for deletion is not found     |
| 400        | Invalid unique key            | The provided unique key is invalid     |

### 1.2 Authorization API

`POST https://fu.andcool.ru/api/register or login` — Registers a new account / logs into an account.
Request limit per minute: 10 times
Both requests accept the same request body but have different errors.

#### Request Example
```json
{
    "username": "Andcool",
    "password": "My cool password"
}
```

Successful execution returns a `200` status code, indicating successful registration / login.
```json
{
    "status": "success",
    "accessToken": <token>,
    "username": "My cool username",
    "message": "logged in with password"
}
```

#### Possible Errors
**Common for both requests:**<br>
| errorId    | message                                                | Reasons                                           |
|------------|--------------------------------------------------------|---------------------------------------------------|
| 2          | No username/password provided                          | Username/password fields are missing in the request |

**Errors for /register:**<br>
| errorId    | message                                                | Reasons                                           |
|------------|--------------------------------------------------------|---------------------------------------------------|
| 1          | An account with this name is already registered        | A user with the given username already exists     |

**Errors for /login:**<br>
| errorId    | message                                                | Reasons                                           |
|------------|--------------------------------------------------------|---------------------------------------------------|
| 3          | Wrong password                                         | Incorrect password                                |
| 4          | User not found                                         | Username not found                                |

`POST https://fu.andcool.ru/api/refresh_token` — Refreshes the token.<br>
Request limit per minute: 10 times<br>
The request body includes the `accessToken` field containing only the token (without Bearer).<br>
Successful execution returns a `200` status code along with the `accessToken` field in the request body, containing the new token.<br>

#### Possible Errors
| errorId    | message                                                | Reasons                                           |
|------------|--------------------------------------------------------|---------------------------------------------------|
| 5          | No access token provided                               | The `accessToken` field is missing in the request |

Errors described in section `1.1` may also occur.

`POST https://fu.andcool.ru/api/logout` — Logs out of the account.<br>
Request limit per minute: 10 times<br>
It takes the `Authorization` header containing the access token.<br>
Successful execution of the request deletes the provided token and returns a `200` status code.<br>

#### Possible Errors
Errors described in section `1.1` may occur as well.<br>