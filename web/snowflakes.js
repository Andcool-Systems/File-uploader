function getRandomInt(min, max){ return Math.floor(Math.random() * (max - min + 1)) + min; }

let object_array = [];

class Circle{
    constructor(object){
        this.object = object;
        this.cnavas_width = 200;
        this.vw = window.innerWidth;
        this.vh = window.innerHeight;

        this.posX = getRandomInt(0, this.vw);
        this.posY = getRandomInt(-this.vw, -50);

        this.speedX = 5;
        this.speedY = 1;

        this.last_time = 0;
        this.last_set = 1;
        this.random_time = getRandomInt(1000, 5000);
        this.random_sin_mod = getRandomInt(1, 3);
        this.last_scroll = document.documentElement.scrollTop || document.body.scrollTop;
    }

    tick(){
        let now_time = Date.now();

        const circle = this.object;
        this.posY += this.speedY;
        this.posX += Math.sin(now_time / 1000) * this.random_sin_mod;

        if (this.posY > this.vh){ this.posY = getRandomInt(-this.vw, -50); }
        if (this.posX > this.vw){ 
            this.posX = -10;
        }
        if (this.posX < -10){ this.posX = this.vw; }
        this.posY -= (document.documentElement.scrollTop || document.body.scrollTop) - this.last_scroll;

        if (now_time - this.last_time > this.random_time){
            this.last_time = now_time;
            this.random_time = getRandomInt(1000, 5000);
            this.random_sin_mod = getRandomInt(1, 3);
        }

        circle.style.left = this.posX + 'px';
        circle.style.top = this.posY + 'px';
        this.last_scroll = document.documentElement.scrollTop || document.body.scrollTop;

    }
}
function run_anim(){
    let table = document.getElementById('canvas');
    let vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    let count = 30

    const date = new Date();
    let day = date.getDate();
    let month = date.getMonth() + 1;
    if (!((month == 12 && day > 20) || (month == 1 && day < 5)) || vw < 900) return;
    
    if( localStorage.getItem("disable_snow"))return;
    
    let snow_btn = document.getElementById('snow_btn');
    snow_btn.style.display = "block";
    table.style.display = "block";

    for (let x = 0; x < count; x++){
        var snowflake = document.createElement("p");
        snowflake.innerHTML = "*";
        snowflake.className = "snowflake";
        table.appendChild(snowflake);
        object_array.push(new Circle(snowflake));
        
    }
}
function tick(){
    for (const snowflake of object_array){
        snowflake.tick();
    }
}

setInterval(tick, 16);


function stop_anim(){
    object_array = [];
    let table = document.getElementById('canvas');
    table.innerHTML = "";
    table.style.display = "none";
}


addEventListener("DOMContentLoaded", (event) => {
    run_anim();
});