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
    }

    tick(){
        let now_time = Date.now();

        const circle = this.object;
        this.posY += this.speedY;
        this.posX += Math.sin(now_time / 1000) * this.random_sin_mod;
        if (this.posY > this.vh){ this.posY = getRandomInt(-this.vw, -50); }
        if (this.posX > this.vw){ this.posX = -50; }
        if (this.posX < -10){ this.posX = this.vw; }

        if (now_time - this.last_time > this.random_time){
            this.last_time = now_time;
            this.random_time = getRandomInt(1000, 5000);
            this.random_sin_mod = getRandomInt(1, 3);
        }

        circle.style.left = this.posX + 'px';
        circle.style.top = this.posY + 'px';
        //circle.style.width = "5px";
        //circle.style.height = "5px";

    }
}
function run_anim(){
    let table = document.getElementById('canvas');
    let vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    let count = 30//Math.round(vw * vh / 10000);


    const date = new Date();
    let day = date.getDate();
    let month = date.getMonth() + 1;
    if (!((month == 12 && day > 20) || (month == 1 && day < 15)) || vw < 900) {
        let snow_btn = document.getElementById('snow_btn');
        snow_btn.style.display = "none";
        return;
    }
    if( localStorage.getItem("disable_snow")){
        return;
    }

    for (let x = 0; x < count; x++){
        var snowflake = document.createElement("p");
        snowflake.innerHTML = "*";
        snowflake.className = "snowflake";
        table.appendChild(snowflake);
        object_array.push(new Circle(snowflake))
    }

    function tick(){
        for (const snowflake of object_array){
            snowflake.tick();
        }
    }

    setInterval(tick, 16);
}

function stop_anim(){
    object_array = [];
    let table = document.getElementById('canvas');
    table.style.display = "none";
}


addEventListener("DOMContentLoaded", (event) => {
    run_anim();
});