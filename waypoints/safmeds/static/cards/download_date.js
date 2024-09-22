$(document).ready(function(){
  document.getElementById("end").valueAsDate = new Date()
  $(".button").click(function(e){
      var start = new Date($("#start").val());
      var end = new Date($("#end").val());
      if ( !!start.valueOf() && !!end.valueOf() && start <= end) {
        var old_ref = $(this).attr("href");
        var new_ref = old_ref + "?startyear=" + start.getFullYear().toString() + "&startmonth=" + start.getMonth().toString() + "&startday=" + start.getDate().toString() + "&endyear=" + end.getFullYear().toString() + "&endmonth=" + end.getMonth().toString() + "&endday=" + end.getDate().toString();
        e.originalEvent.currentTarget.href = new_ref;
      } else {
        e.preventDefault();
        alert("Please enter a valid date range.");
      }
  });
});
