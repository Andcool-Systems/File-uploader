let api_upload_url = "/api/upload";
let api_file_url = "/file/";
let api_url = "https://fu.andcool.ru";
//let api_url = "http://127.0.0.1:8080";

async function delete_file(data, id){
	let confirmed = confirm("Delete it? It will be impossible to restore the file!");
	if (confirmed){
		let response = await axios.delete(api + "/api/delete/" + data.file_url + "?key=" + data.key);
		if (response.status == 200){
			if (!data.synced){
				let old_data = JSON.parse(localStorage.getItem("file_history") || "[]");
				old_data.splice(id, 1);
				localStorage.setItem("file_history", JSON.stringify(old_data));
			}
			document.getElementById("row_" + id).remove();
		}
	}
}


function append_to_files_arr(data, id){
  	let table = document.getElementById('files_table');

  	// Insert a row at the start of table
  	let newRow = table.insertRow(0);
	newRow.id = "row_" + id;

  	// Insert a cell at the end of the row
  	let newCell = newRow.insertCell();
    let newCell2 = newRow.insertCell();
    // Append a text node to the cell
    let url = document.createElement("a");
    url.innerHTML = data['file_url_full'];
	url.id = "url";
	//url.onclick = function(){navigator.clipboard.writeText(data['file_url_full']);}
	url.href = data['file_url_full'];
	url.target = "_blank";

	let filename = document.createElement("p");
    filename.innerHTML = data['user_filename'];
	filename.id = "filename";

	let creation_date_div = document.createElement("div");
	creation_date_div.id = "creation_date_div";

	let cr_time = document.createElement("p");
    cr_time.innerHTML = data['creation_date'];
	cr_time.id = "cr_time";

    const button = document.createElement('button');
    button.innerHTML = 'Delete';
	button.onclick = function(){delete_file(data, id);}

	let online = document.createElement("img");
	online.className = "online";
	if (data.synced){
		online.src = "./res/globe_on.png";
		online.title = "Synchronized with the server";
	}else{
		online.src = "./res/globe_off.png";
		online.title = "Stored on local browser";
	}

	let urls_div = document.createElement("div");
	urls_div.appendChild(url);
	urls_div.appendChild(filename);

	creation_date_div.appendChild(cr_time);
	creation_date_div.appendChild(online);
	urls_div.appendChild(creation_date_div);

    newCell.appendChild(urls_div);
    newCell2.appendChild(button);
}

async function get_new_tokens(accessToken){
	try{
		let response = await axios.post(api_url + "/api/refresh_token", {'accessToken': accessToken}, {})
		if (!response) return false;
		if (response.status != 200) return false;
		return response.data.accessToken;
	}catch{
		return false;
	}
}

async function fetch_files(accessToken, len){
	if (!accessToken) return [];
	if (!checkAccess(accessToken)){
		let new_access = await get_new_tokens(accessToken);
		if (!new_access){
			localStorage.removeItem("accessToken");
			return [];
		}
		console.log(new_access);
		accessToken = new_access;
		localStorage.setItem("accessToken", new_access);
	}
	try{
		let response = await axios.get(api_url + "/api/getFiles", {
			headers: {
				'Authorization': 'Bearer ' + accessToken
			}
		})
		if (!response) return;
		if (response.status == 400){
			localStorage.removeItem("accessToken");
			return [];
		}

		let logim_page_btn = document.getElementById('login_page_a');
		logim_page_btn.textContent = "Logout";
		logim_page_btn.href = "/";
		logim_page_btn.onclick = function() {if (confirm("Log out?")) {logout()}};

		document.getElementById('login_mess').style.display = "none";
		let it = 0;
		for (const file of response.data.data){
			append_to_files_arr(file, len + it);
			it++;
		}

	}catch{
		localStorage.removeItem("accessToken");
		return [];
	}
}

async function logout(){
	let accessToken = localStorage.getItem("accessToken");
	console.log(accessToken);
	if (!accessToken) return [];
	if (!checkAccess(accessToken)){
		let new_access = await get_new_tokens(accessToken);
		if (!new_access){
			localStorage.removeItem("accessToken");
			return [];
		}
		console.log(new_access);
		accessToken = new_access;
		localStorage.setItem("accessToken", new_access);
	}
	try{
		let response = await axios.post(api_url + "/api/logout", {}, {
			headers: {
				'Authorization': 'Bearer ' + accessToken
			}
		})
		if (!response) return;
		if (response.status == 400 || response.status == 200){
			localStorage.removeItem("accessToken");

			let logim_page_btn = document.getElementById('login_page_a');
			logim_page_btn.textContent = "Login";
			logim_page_btn.href = "https://fu.andcool.ru/login/";

		}
	}catch{
		localStorage.removeItem("accessToken");
		return [];
	}
}

addEventListener("DOMContentLoaded", (event) => {
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
			if (file.size > 100 * 1024 * 1024){
				load_mess.textContent = "File size exceeds the limit (100MB)";
				return;
			}
			upload(file);
		};

		reader.readAsDataURL(file); 
		}
	});

	let file_history = JSON.parse(localStorage.getItem("file_history") || "[]");
	if (file_history != []){
		let it = 0;
		for (const file of file_history){
			append_to_files_arr(file, it);
			it++;
		}
	}
	fetch_files(localStorage.getItem("accessToken"), file_history.length);


	let dropContainer = document.getElementById('dropContainer')
	dropContainer.ondragover = dropContainer.ondragenter = function(evt) {
		evt.preventDefault();
	  };
	  
	dropContainer.ondrop = function(evt) {
		const dT = new DataTransfer();
		dT.items.add(evt.dataTransfer.files[0]);
		document.getElementById('input_file').files = dT.files;
		document.getElementById('input_file').dispatchEvent(new Event('change'))
		evt.preventDefault();
	};
});


async function upload(file){
    
    let imagefile = document.querySelector('#input_file');
    let load_mess = document.getElementById('load_mess');
	let file_ext = document.getElementById('include_ext');
    load_mess.textContent = "Uploading to the server...";

    try{
      	let response = await axios.post(api_url + api_upload_url + "?include_ext=" + file_ext.checked, {'file': file}, {
          	headers: {
          	'Content-Type': 'multipart/form-data',
			'Authorization': 'Bearer ' + localStorage.getItem("accessToken")
          	}
      	})

      	imagefile.value = "";
      	if (response){
          	if (response.status == 200){
              	let response1 = response.data;
				var currentdate = new Date(); 
				var datetime = currentdate.getDate() + "."
						+ (currentdate.getMonth()+1)  + "." 
						+ currentdate.getFullYear() + " "  
						+ currentdate.getHours() + ":"  
						+ currentdate.getMinutes() + ":" 
						+ currentdate.getSeconds();
				

				response1["creation_date"] = datetime;
				load_mess.textContent = "Uploaded!";

				
				let old_data = JSON.parse(localStorage.getItem("file_history") || "[]");
				append_to_files_arr(response1, old_data.length)

				navigator.clipboard.writeText(response1['file_url_full']);
				
				if (!response1.synced){
					old_data.push(response1);
					localStorage.setItem("file_history", JSON.stringify(old_data));
				}
          	}
          	else if (response.status == 429){
              	load_mess.textContent = "Too many requests (2 per minute)";
          	}else{
              	load_mess.textContent = response.data.message;
          	}	
      	} 
    }catch(err){
      	console.log(err);
      	load_mess.textContent = "Error while uploading file. See console for more information.";
		imagefile.value = "";
    }
  
}

