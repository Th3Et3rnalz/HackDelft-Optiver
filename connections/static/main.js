console.log("The file was found");

var new_data = 0;
var previous_data = 0;
var playing = 0;

var text_data = document.getElementById("filler");
const socket = io('http://localhost:8080');

function sendMsg() {
    socket.emit("demand", "I demand your data");
}


socket.on("data", function(data) {
    if (new_data == 0){
        previous_data = data
        new_data = 1
    }

    // console.log(data)
    update_widgets(data);
    addData(data);
})

socket.on('first_connect', function(username) {
    window.sid = username;
    console.log("This is my SID: " + window.sid);
});


socket.on('set_main_user', function(sid) {
    if (window.sid == sid) {
        window.setInterval(requestdata, 1500);
        console.log("Hey, I'm the first");
    }
});


function requestdata(){
    socket.emit("demand", "I demand your data");
}
console.log("the file was run");


// GRAPH DATA  GRAPH DATA  GRAPH DATA  GRAPH DATA  GRAPH DATA  GRAPH DATA  GRAPH DATA  GRAPH DATA

var config1 = {
    type: 'line',
    data: {
        datasets: [{
            label: 'Locked PnL',
            backgroundColor: '#E95E40',
            data: [],
            fill: true,
        }]
    },
    options: {
        scales: {
          xAxes: [{
            type: 'linear',
            display: true,
            scaleLabel: {
              display: true,
              labelString: 'time [s]'
            }
          }],
          yAxes: [{
            display: true,
            scaleLabel: {
              display: true,
              labelString: 'PnL value'
            }
          }]
        }
    }
};

window.user;

function addData(data_from_server) {
    console.log("Adding data to plot");
    user = validateForm();
    user = user[0];
    var new_config = config1;
    // console.log(data_from_server.length);
    // console.log(new_config.data.datasets[0].data.length);
    for (i = new_config.data.datasets[0].data.length; i < data_from_server.length; i++) {
      var data_to_add = {x: data_from_server[i][user].time,
                         y: data_from_server[i][user].lpnl}
      // console.log(data_to_add)
      // console.log(data_from_server.length);
      // console.log(new_config.data.datasets[0].data.length);
      new_config.data.datasets[0].data.push(data_to_add);
    }
    config1 = new_config;
    // console.log(new_config.data.datasets[0].data)
    window.myLine1.update();
}

function validateForm() {
  user = document.forms["myForm"]["fname"].value;
  // console.log(user, typeof user);
  if (user == ""){
    user = document.getElementById("username").innerHTML;
    // alert(user);
    var change = "False";
  }
  else {
    document.getElementById("username").innerHTML = user;
    var change = "True";
  }
  return [user, change]
}


function update_widgets(data_from_server) {
  var user = validateForm()
  user = user[0];
  var change = user[1];
  // console.log(typeof user);
  var username = document.getElementById('username');
  var pnl = document.getElementById('pnl');
  var pnl_locked = document.getElementById('pnl_locked');
  var ping = document.getElementById('ping');
  var status = document.getElementById('status');
  var sp = document.getElementById('sp');
  var esx = document.getElementById('esx');
  var volume = document.getElementById('volume');
  var exposure = document.getElementById('exposure');

  exposure_data = data_from_server[data_from_server.length  -1][user].exposure;
  console.log(exposure_data);
  e_data = Number(exposure_data);
  if (e_data < -1000){
    exposure.parentNode.style.backgroundColor = "red";

  } else if (1000 <= e_data && e_data <= 1000) {
    exposure.parentNode.style.backgroundColor = "yellow";
  } else if (e_data > 1000) {
    exposure.parentNode.style.backgroundColor = "green";
  }
  if (e_data > 0){
    exposure_data = "+" + String(exposure_data)
  }
  exposure.innerHTML = String(exposure_data);
  if (change == "True"){
      username.innerHTML = String(data_from_server[data_from_server.length - 1][user].username);
  }
  else {
    console.log("color should have changed");
  }
  pnl.innerHTML = String(data_from_server[data_from_server.length - 1][user].pnl);
  pnl_locked.innerHTML = String(data_from_server[data_from_server.length - 1][user].lpnl);
  volume.innerHTML = String(data_from_server[data_from_server.length - 1][user].volume);
  esx.innerHTML = String(data_from_server[data_from_server.length - 1][user].esx);
  sp.innerHTML = String(data_from_server[data_from_server.length - 1][user].sp);
}


window.onload = function() {
    var canvas1 = document.getElementById('canvas1').getContext('2d');
    window.myLine1 = new Chart(canvas1, config1);
};
