# File Uploader

The file uploader is implemented in the Python programming language using FastAPI. All uploaded files are stored on the server. The API provides the ability to preview and download files based on their file extensions.  

## API Documentation

The API is currently hosted at [fu.andcool.ru](https://fu.andcool.ru/).   
Page redirection is handled through the nginx proxy server. The API consists of 2 pathes:  

- `/file/` – Endpoint where all files are located.
- `/api/` – Main API endpoint

### 1.1 Authorization Errors

All requests requiring the `Authorization` header may encounter errors related to authorization issues.   
The `Authorization` header should have the format `Authorization: Bearer <token>`.  

#### Response Example

All errors of this type follow a consistent response format and always return an HTTP code of `401`.   
This section will be referred to as `1.1` in the documentation.  

```json
{
    "status": "error",
    "message": "Auth error",
    "auth_error": {
        "message": "error message",
        "errorId": <error code>
    }
}
```

**List of errors:** 

| errorId | message                                                | Reasons                                            |
| ------- | ------------------------------------------------------ | -------------------------------------------------- |
| -1      | No Authorization header provided                       | The request is missing the `Authorization` header  |
| -2      | Authorization header must have `Bearer <token>` format | The `Authorization` header has an incorrect format |
| -3      | Access token expired                                   | The token has expired                              |
| -4      | Invalid access token                                   | The token cannot be decrypted                      |
| -5      | Token not found                                        | The token is not found                             |

### 1.2 Basic API

### Retrieve a file based on the URL.
`GET /file/<file_url>` or `GET /f/<file_url>`  
Successful execution returns a `200` status code and the binary file with the `Content-Type`.   
If the file type cannot be determined, the API returns the file in download mode.  

#### Possible Errors

| Error Code | Description    | Possible Reasons                               |
| ---------- | -------------- | ---------------------------------------------- |
| 404        | File not found | The file referenced by the code does not exist |

### Upload a file to the server
`POST /api/upload/{group_id}?include_ext=false`   
The request body should contain the file to be uploaded.   
Only one file is allowed, and its size should not exceed 100MB.   
The maximum request frequency is **2 per minute**.    

**Query params:**  
> The `group_id` parameter indicates the group to which the file should be uploaded. The parameter can take the value `private`, which means that the file must be linked to a personal account. When passing the `group_id` parameter other than the `private` Authorization header is required.  

**Request body:**  
> **The `Content-Type` header of the request must be a `multipart/form-data`**  
The file must be have `file` key in request body.  
The query parameter `include_ext` can be set to `true/false` to indicate whether the file extension should be included in the file URL.  

**Request headers:**  
>The request can also include the `Authorization` header, containing the user's unique token.
If the token is not provided or is not valid, the `synced` field in the response body will be set to `false`. The file will be uploaded to the server regardless of whether the `Authorization` header is included in the request. The `auth_error` field in the response body contains the authentication error (section `1.1`), and if there is no error, the field will be `{}`.  

#### Response Example
On successful execution, the API returns a `200` HTTP code along with a JSON response.  

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
| Error Code | message                             | Possible Reasons                                                               |
| ---------- | ----------------------------------- | ------------------------------------------------------------------------------ |
| 400        | No file uploaded                    | No file is given in the request body                                           |
| 413        | File size exceeds the limit (100MB) | The file size exceeds 100MB                                                    |
| 400        | Invalid group id                    | `group_id` parameter contains non-numerical value                              |
| 404        | Group not found                     | The group wuth provided `group_id` not found                                   |
| 403        | You are not in the group            | Group is exists, but you are has not permissions to upload files in this group |

### Delete a file
`GET /api/delete/<file_url>?key=<unique key>`  
Successful execution returns a `200` status code, removing the file from the server.  

#### Possible Errors

| Error Code | Description        | Possible Reasons                   |
| ---------- | ------------------ | ---------------------------------- |
| 404        | File not found     | The file for deletion is not found |
| 400        | Invalid unique key | The provided unique key is invalid |

### 1.2 Authorization API
### Login and register
`POST /api/register`  
`POST /api/login`  
Request limit per minute: 10 times.  
Both requests accept the same request body but have different errors.  
> A Boolean value can be passed to the optional query parameter `bot`. When `bot` is true, a token with a lifetime of 6 months will be generated.

#### Request Example

```json
{
    "username": "My cool username",
    "password": "My cool password"
}
```

Successful execution returns a `200` HTTP code, indicating successful registration / login.  

```json
{
    "status": "success",
    "accessToken": "<token>",
    "username": "My cool username",
    "message": "logged in with password"
}
```

### Possible Errors

**Common for both requests:**

| errorId | HTTP code | message                       | Reasons                                             |
| ------- | --------- | ----------------------------- | --------------------------------------------------- |
| 2       | 400       | No username/password provided | Username/password fields are missing in the request |

**Errors for /register:**

| errorId | HTTP code | message                                         | Reasons                                       |
| ------- | --------- | ----------------------------------------------- | --------------------------------------------- |
| 1       | 400       | An account with this name is already registered | A user with the given username already exists |

**Errors for /login:**

| errorId | HTTP code | message        | Reasons            |
| ------- | --------- | -------------- | ------------------ |
| 3       | 400       | Wrong password | Incorrect password |
| 4       | 404       | User not found | Username not found |

### Refreshe the token
`POST /api/refresh_token`  
Request limit per minute: 10 times.   
The request body includes the `accessToken` field containing only the token (without `Bearer`).   
Successful execution returns a `200` HTTP code along with the `accessToken` field in the request body, containing the new token.  

#### Possible Errors

| errorId | HTTP code | message                  | Reasons                                           |
| ------- | --------- | ------------------------ | ------------------------------------------------- |
| 5       | 400       | No access token provided | The `accessToken` field is missing in the request |

Errors described in section `1.1` may also occur.  

### Log out of the account
`POST /api/logout`     
Request limit per minute: 10 times.   
Endpoint takes the `Authorization` header containing the access token.   
Successful execution of the request deletes the provided token and returns a `200` HTTP code  

#### Possible Errors

Errors described in section `1.1` may occur as well.  


### Get a list of files.
`GET /api/get_files/{group_id}`  
It takes the `Authorization` header containing the access token.   
Retrieves a list of all files associated with this account.  

> The `group_id` parameter shows which group to get the files from. If the parameter is set to `private`, the files will be taken from a personal account, otherwise Authorization header is required

#### Response Example

```json
{
    "status": "success",
    "message": "files got successfully",
    "username": "My cool username",
    "is_group_owner": true,
    "data": [
        {
            "file_url": "4yn-8yjhsu",
            "file_url_full": "https://fu.andcool.ru/file/4yn-8yjhsu",
            "key": "6b9a1c1b-5594-4cb9-8d49-99a4c28782a1",
            "ext": ".mp4",
            "user_filename": "test.mp4",
            "creation_date": "1.1.1971",
            "synced": true
        },
        {
            "file_url": "4yn-8yjhsR",
            "file_url_full": "https://fu.andcool.ru/file/4yn-8yjhsR",
            "key": "6b9a1c1b-5594-4cb9-8d49-99a4c28782a1",
            "ext": ".mp4",
            "user_filename": "test1.mp4",
            "creation_date": "1.1.1971",
            "synced": true
        }
    ]
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message                  | Possible Reasons                                                               |
| ---------- | ------------------------ | ------------------------------------------------------------------------------ |
| 400        | Invalid group id         | `group_id` parameter contains non-numerical value                              |
| 404        | Group not found          | The group wuth provided `group_id` not found                                   |
| 403        | You are not in the group | Group is exists, but you are has not permissions to upload files in this group |


### Transfer local files to an account.
`POST /api/transfer`  
It takes the `Authorization` header containing the access token.  

> The request transfers local files to the account. The endpoint takes files from the `data` field in the request body and sequentially binds each file to an account. If the binding of any file failed, then these files will be returned in the response body in the `unsuccess` field. The file is transferred by their `file_url` and `key`

#### Request body example
```json
{   
    "data":[
        {
            "file_url": "4yn-8yjhsu",
            "key": "6b9a1c1b-5594-4cb9-8d49-99a4c28782a1"
        },
        {
            "file_url": "4yn-8yjhsR",
            "key": "6b9a1c1b-5594-4cb9-8d49-99a4c28782a1"
        }
    ]
}
```

#### Response example

```json
{
    "status": "success",
    "message": "transfered", 
    "unsuccess": [
        {
            "file_url": "4yn-8yjhsR",
            "key": "6b9a1c1b-5594-4cb9-8d49-99a4c28782a1"
        }
    ]
}

```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message                         | Possible Reasons                               |
| ---------- | ------------------------------- | ---------------------------------------------- |
| 400        | Couldn't parse request body     | No request body provided                       |
| 400        | No `data` field in request body | Couldn't not find `data` field in request body |

## Groups

### Create file group
`POST /api/create_group`  
It takes the `Authorization` header containing the access token.  
> Creates a group with the passed name. The maximum length of a group name is 50 characters.

#### Request body example
```json
{   
    "group_name": "New group"
}
```

#### Response example

```json
{
    "status": "success",
    "message": "created",
    "name": "New group",
    "group_id": 12345678,
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message                               | Possible Reasons                                     |
| ---------- | ------------------------------------- | ---------------------------------------------------- |
| 400        | No `group_name` provided              | Couldn't not find `group_name` field in request body |
| 400        | Group name length exceeded (50 chars) | Too long group name                                  |

### Delete file group
`DELETE /api/delete_group/{group_id}`  
It takes the `Authorization` header containing the access token.  
> Deletes a group with the passed `group_id`.


#### Response example

```json
{
    "status": "success", 
    "message": "deleted"
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message                                            | Possible Reasons                       |
| ---------- | -------------------------------------------------- | -------------------------------------- |
| 404        | Group not found                                    | Group with passed `group_id` not found |
| 403        | You dont have any permissions to delete this group | You are not owner of this group        |

### Generate a new invite link
`GET /api/generate_invite/{group_id}`  
It takes the `Authorization` header containing the access token.  
> Generates a invite link for group with the passed `group_id`.


#### Response example

```json
{
    "status": "success",
    "message": "created",
    "invite_link": "https://fu.andcool.ru/invite/DSAfd4-hpoqFDFj"
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message                       | Possible Reasons                       |
| ---------- | ----------------------------- | -------------------------------------- |
| 404        | Group not found               | Group with passed `group_id` not found |
| 403        | You dont have any permissions | You are not owner of this group        |

### Join to a group
`POST /api/join/{invite_link}`  
It takes the `Authorization` header containing the access token.  
> Joins to a group by passed `invite_link`.


#### Response example

```json
{
    "status": "success",
    "message": "created",
    "name": "New group",
    "group_id": 12345678,
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message                      | Possible Reasons              |
| ---------- | ---------------------------- | ----------------------------- |
| 404        | Invite link not found        | Could not found a invite link |
| 400        | You are already in the group | You are already in the group  |


### Leave from group
`POST /api/leave/{group_id}`  
It takes the `Authorization` header containing the access token.  
> Leaves from group with passed `group_id`


#### Response example
```json
{
    "status": "success", 
    "message": "leaved"
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message                  | Possible Reasons                       |
| ---------- | ------------------------ | -------------------------------------- |
| 404        | Group not found          | Group with passed `group_id` not found |
| 400        | You are not in the group | You are not in the group               |


### Get info about invite link
`GET /api/invite_info/{invite_link}`  
It takes the `Authorization` header containing the access token.  
> Gives an information about group about invite link.


#### Response example
```json
{
    "status": "success",
    "message": "created",
    "name": "New group",
    "group_id": 12345678,
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
| Error Code | message               | Possible Reasons              |
| ---------- | --------------------- | ----------------------------- |
| 404        | Invite link not found | Could not found a invite link |


### Get all group from account
`GET /api/get_groups`  
It takes the `Authorization` header containing the access token.  
> Get list of groups linked to an account.


#### Response example
```json
{
    "status": "success", 
    "message": "groups got successfully", 
    "groups": [
        {
            "name": "Bim-Bim",
            "group_id": 12345679
        },
        {
            "name": "Bam-Bam",
            "group_id": 12345677
        }
    ]
}
```

#### Possible Errors

Errors described in section `1.1` may occur as well.  
