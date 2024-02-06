//let api = "http://127.0.0.1:8080";
let api = "https://fu.andcool.ru";

function moveToPage(page_url){
    const protocol = window.location.protocol;
    const host = window.location.host;
    window.location.replace(protocol + "//" + host + page_url);
}

function parseJwt (token) {
    var base64Url = token.split('.')[1];
    var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    var jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));

    return JSON.parse(jsonPayload);
}

function checkAccess(token) {
    var secondsSinceEpoch = Date.now() / 1000
    res = parseJwt(token);
    
    return (parseInt(res["ExpiresAt"]) - 259200) > secondsSinceEpoch;
}

async function register(){
    let username = document.getElementById('reg_username').value;
    let pass = document.getElementById('reg_pass').value;
    let error_mess = document.getElementById('reg_error');

    if (username && pass){
        try{
            let response = await axios.post(api + "/api/register", 
                                            {'username': username, "password": pass}, {})

            if (!response){ return; }
            if (response.status == 200){
                console.log(response.data);
                localStorage.setItem("accessToken", response.data.accessToken);
                setTimeout(moveToPage("/"), 1000); 
            }
            
        }catch(err){
            console.log(err.response.data);
            error_mess.textContent = err.response.data.message;
        }
    }
}

async function login(){
    let username = document.getElementById('log_username').value;
    let pass = document.getElementById('log_pass').value;
    let error_mess = document.getElementById('log_error');

    if (username && pass){
        try{
            let response = await axios.post(api + "/api/login", 
                                            {'username': username, "password": pass}, {})

            if (!response){ return; }
            if (response.status == 200){
                console.log(response.data);
                localStorage.setItem("accessToken", response.data.accessToken);
                setTimeout(moveToPage("/"), 1000); 
            }
            
        }catch(err){
            console.log(err.response.data);
            error_mess.textContent = err.response.data.message;
        }
    }
}