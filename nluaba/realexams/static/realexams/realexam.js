var second_interval;
var start_time;

$(document).ready(function(){
  $("#question_select").change(function(){
    if ($('input[name=answer]:checked').length == 0 && $('input[name=answer]').length != 0){
      select_question(parseInt($("#question_select").val()));
    } else {
      var next_question = $("<input type='hidden' name='next_question' />");
      next_question.attr('value', $("#question_select").val());
      $("form").append(next_question);
      $("form").submit();
    }
  });
  $("input[type=radio]").change(function(){
    $("input[type=submit]").prop("disabled", false);
    $(this).blur();
  });
  $("form").submit(function(){
    if ($('input[name=answer]:checked').length == 0 && $('input[name=answer]').length != 0){
      return false;
    }
    var hidden_input = $("<input type='hidden' name='milliseconds' />");
    hidden_input.attr('value', Date.now()-start_time);
    $("form").append(hidden_input);
    return true;
  });
  $(".navlink").click(function(e){
    if ($('input[name=answer]:checked').length == 0 && $('input[name=answer]').length != 0){
      return true;
    }
    var next_question = $("<input type='hidden' name='next_question' />");
      next_question.attr('value', $(this).data('next-question'));
      $("form").append(next_question);
      $("form").submit();
      return false;
  });
  if (timed){
    start_time = Date.now();
    second_interval = setInterval(function(){
      console.log("Second");
      var timeStr = $("#time_counter").html().split(":");
      var second = parseInt(timeStr[2]) + 1;
      var minute = parseInt(timeStr[1]);
      var hour = parseInt(timeStr[0]);
      if (second == 60){
        second = 0;
        minute = minute + 1;
        if (minute == 60){
          minute = 0;
          hour = hour + 1;
        }
      }
      $("#time_counter").html(("00"+hour.toString()).slice(-2)+":"+("00"+minute.toString()).slice(-2)+":"+("00"+second.toString()).slice(-2));
      if ($("#time_counter").html() == $("#total_time").html()){
        if ($('input[name=answer]:checked').length == 0 && $('input[name=answer]').length != 0){
          test_timeout();
        }
        var timed_out = $("<input type='hidden' name='timed_out' />");
        timed_out.attr('value', "Timed Out");
        $("form").append(timed_out);
        $("form").submit();
      }
    }, 1000);
  }
  $("textarea").keydown(function(){
    $("input[type=submit]").prop("disabled", false);
    $("textarea").off('keydown');
  });
})
