var start_time;

$(document).ready(function(){
  start_time = Date.now();
  $(".select").change(function(){
    if ($('input[class=answer]:checked').length == 0 && $('input[class=answer]').length != 0){
      select_question(parseInt($(".select").val()));
    } else {
      var next_question = $("<input type='hidden' name='next_question' />");
      next_question.attr('value', $(".select").val());
      $("form").append(next_question);
      $("form").submit();
    }
  });
  $("input[type=radio]").change(function(){
    $("input[type=submit]").prop("disabled", false);
    $(this).blur();
  });
  $("input[type=checkbox]").change(function(){
    $("input[type=submit]").prop("disabled", false);
    $(this).blur();
  });
  $("form").submit(function(){
    var hidden_input = $("<input type='hidden' name='milliseconds' />");
    hidden_input.attr('value', Date.now()-start_time);
    $("form").append(hidden_input);
    return true;
  });
  $(".navlink").click(function(e){
    if ($('input[class=answer]:checked').length == 0 && $('input[class=answer]').length != 0){
      return true;
    }
    var next_question = $("<input type='hidden' name='next_question' />");
      next_question.attr('value', $(this).data('next-question'));
      $("form").append(next_question);
      $("form").submit();
      return false;
  });
  $("textarea").keydown(function(){
    $("input[type=submit]").prop("disabled", false);
    $("textarea").off('keydown');
  });
})
