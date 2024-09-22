from django import template

register = template.Library()

def timedelta_display(value):
    return str(value.seconds/3600)+":"+str((value.seconds/60)%60)+":"+str((value.seconds)%60)
