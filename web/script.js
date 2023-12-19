let api_upload_url = "api/upload/"
let api_file_url = "file/"

var api = "https://fu.andcool.ru/"

const apiManager = axios.create({
    baseURL: api,
    withCredentials: false,
    validateStatus: function (status) {
        return status >= 200;
      }
});

document.getElementById('input_file').addEventListener('change', function(e) {
    let fileInput = document.getElementById('input_file');
    let load_mess = document.getElementById('load_mess');

    let file = fileInput.files[0];
    if (file) {
        let reader = new FileReader();

      reader.onprogress = function(e) {
        if (e.lengthComputable) {
            let percentage = (e.loaded / e.total) * 100;
          load_mess.textContent = "Uploading file... " + percentage.toFixed(1) + '%';
        }
      };

      reader.onload = function() {
        console.log('File loaded successfully');
        upload(file);
      };

      reader.readAsDataURL(file); 
    }
  });
    
async function upload(file){
    
    let imagefile = document.querySelector('#input_file');
    let load_mess = document.getElementById('load_mess');
    
    let response = await apiManager.post(api_upload_url, {'file': file}, {
        headers: {
        'Content-Type': 'multipart/form-data'
        }
    })

    imagefile.value = "";
    if (response){
        if (response.status == 200){
            let response1 = response.data;
            let table = document.getElementById('files_table');

            // Insert a row at the end of table
            let newRow = table.insertRow();

            // Insert a cell at the end of the row
            let newCell = newRow.insertCell();
            let newCell2 = newRow.insertCell();
            // Append a text node to the cell
            let newText = document.createElement("p");
            newText.innerHTML = api + api_file_url + response1['file_url'];

            const button = document.createElement('button');
            button.innerHTML = 'Copy';
            button.onclick = function(){navigator.clipboard.writeText(api + api_file_url + response1['file_url']);}

            newCell.appendChild(newText);
            newCell2.appendChild(button);

            load_mess.textContent = "Uploaded!";
        }
        else if (response.status == 429){
            load_mess.textContent = "Too many requests (1 per minute)";
        }else{
            load_mess.textContent = response.data.message;
        }
    } 
    
  
}