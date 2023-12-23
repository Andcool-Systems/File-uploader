let api_upload_url = "/api/upload";
let api_file_url = "/file/";
let api = "https://fu.andcool.ru";

async function delete_file(url, key, id){
	console.log(url);

	let confirmed = confirm("Delete it? It will be impossible to restore the files!");
	if (confirmed){
		let response = await axios.delete(api + "/api/delete/" + url + "?key=" + key);
		if (response.status == 200){
			let old_data = JSON.parse(localStorage.getItem("file_history") || "[]");
			old_data.splice(id, 1);
			localStorage.setItem("file_history", JSON.stringify(old_data));

			let table = document.getElementById('files_table');
			table.innerHTML = "";

			if (old_data != []){
				console.log(old_data);
				let it = 0;
				for (const file of old_data){
					append_to_files_arr(file, it);
					it++;
				}
			}
		}
	}
}


function append_to_files_arr(data, id){
  	let table = document.getElementById('files_table');

  	// Insert a row at the start of table
  	let newRow = table.insertRow(0);

  	// Insert a cell at the end of the row
  	let newCell = newRow.insertCell();
    let newCell2 = newRow.insertCell();
    // Append a text node to the cell
    let url = document.createElement("p");
    url.innerHTML = data['file_url_full'];
	url.id = "url";
	url.onclick = function(){navigator.clipboard.writeText(data['file_url_full']);}

	let filename = document.createElement("p");
    filename.innerHTML = data['user_filename'];
	filename.id = "filename";

	let cr_time = document.createElement("p");
    cr_time.innerHTML = data['creation_date'];
	cr_time.id = "cr_time";

    const button = document.createElement('button');
    button.innerHTML = 'Delete';
	button.onclick = function(){delete_file(data['file_url'], data['key'], id);}

	let urls_div = document.createElement("div");
	urls_div.appendChild(url);
	urls_div.appendChild(filename);
	urls_div.appendChild(cr_time);

    newCell.appendChild(urls_div);
    newCell2.appendChild(button);
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
		console.log(file_history);
		let it = 0;
		for (const file of file_history){
			append_to_files_arr(file, it);
			it++;
		}
	}
});


async function upload(file){
    
    let imagefile = document.querySelector('#input_file');
    let load_mess = document.getElementById('load_mess');
	let file_ext = document.getElementById('include_ext');
    load_mess.textContent = "Uploading to the server...";

    try{
      	let response = await axios.post(api + api_upload_url + "?include_ext=" + file_ext.checked, {'file': file}, {
          	headers: {
          	'Content-Type': 'multipart/form-data'
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

				let old_data = JSON.parse(localStorage.getItem("file_history") || "[]");
              	append_to_files_arr(response1, old_data.length)

              	load_mess.textContent = "Uploaded!";

				navigator.clipboard.writeText(response1['file_url_full']);

			  	old_data.push(response1);
			  	localStorage.setItem("file_history", JSON.stringify(old_data));
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