var timing_start;
var timeout;
var temp_interval;
var index = 0;
var responses = [];
var rand_name;
var stimulus_start;
var ended = false;

function makeName() {
  var text = "";
  var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

  for (var i = 0; i < 5; i++){
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

function sleep(delay) {
  var start = new Date().getTime();
  while (new Date().getTime() < start + delay);
}

function end(auto=false){
  if (ended == false){
    ended = true;
  var timing_end = Date.now();
  payload = {"responses": JSON.stringify(responses), "deck":deck, "practice_type":practice_type}
  payload['duration'] = timing_end - timing_start;
  if (auto){
    report(payload, function(){
      console.log("Done");
    })
  } else {
    report(payload, function(){
      $("#card").empty();
      $("#card").html("You're all done! Press the button below to return to the menu.");
      $("#finish").show();
      $("#finish").focus();
    });
  }
}}

$(document).ready(function(){
  $("#next").prop("disabled", true);
  rand_name = makeName();
  $(".real_input").attr('id', 'response_' + rand_name);
  console.log('response_' + rand_name);
  $("#feedback").hide();
  $("#finish").hide();
  $("#finish").click(function(){
    window.location = "/safmeds/decks";
  });
  $("#definition").html(cards[index]['definition']);
  $(".real_input").focus();
  $(".real_input").on("keypress", function(event){
    $("#next").prop("disabled", true);
    $(".real_input").off("keypress");
    timing_start = Date.now();
    stimulus_start = Date.now();
    if (practice_type == "minute"){
      timeout = setInterval(function(){
        clearInterval(timeout);
        $(".real_input").prop("disabled", true);
        responses.push({'card_id':cards[index]['id'], 'response':$(".real_input").val(), 'latency':Date.now()-stimulus_start});
        end();
      }, 60000);}
    $(".real_input").on("keypress", function(event){
      if (event.keyCode == 13){
        $("#next").click();
      }
    });
  });
  $("#next").click(function(event){
    if (index + 1 >= cards.length && timeout){
      clearInterval(timeout);
    }
    $("#next").prop("disabled", false);
    $(".real_input").prop("disabled", true);
    responses.push({'card_id':cards[index]['id'], 'response':$(".real_input").val(), 'latency':Date.now()-stimulus_start});
    if ($(".real_input").val().toUpperCase().replace("`", "'").trim() == cards[index]['term'].toUpperCase().replace("`", "'")){
      $("#feedback").html("Correct");
    } else {
      $("#feedback").html("Incorrect");
      $(".real_input").val(cards[index]['term']);
    }
    $("#feedback").show();
    temp_interval = setTimeout(function(){
      index += 1;
      if (index >= cards.length){
        end();
        return;
      }
      $("#feedback").hide();
      $("#definition").html(cards[index]['definition']);
      $("#next").prop("disabled", false);
      $(".real_input").prop("disabled", false);
      $(".real_input").val("");
      $(".real_input").focus();
      stimulus_start = Date.now();
    }, 1000);
  });
  $(window).on("beforeunload", function(e){
    console.log("Unload");
    $(".real_input").prop("disabled", true);
    responses.push({'card_id':cards[index]['id'], 'response':$(".real_input").val(), 'latency':Date.now()-stimulus_start});
    end(true);
    sleep(2000);
  });
  $(".real_input").css("height", "35px");
});
