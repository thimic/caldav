from caldav import DAVClient
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import uuid
import sys

## Set up three clients and three principals.  
clients = [
    DAVClient(username = "testuser%i" % i, password = "testpass%i" %i, url = "http://calendar.tobixen.no/caldav.php/")
    for i in (1,2,3)
]

if not clients[0].check_scheduling_support():
    print("Server does not support RFC6638")
    sys.exit(1)

## testuser1 (that's clients[0] / principal[0])  wants to set up a meeting
## involving testuser2 and testuser3.

## testuser2 and testuser3 (on client[1] / principal[1] and
## client[2] / principal[2]) needs to respond to the RSVP.

principals = [ c.principal() for c in clients ]

demo_calendars = [
    p.make_calendar(name="calendar for scheduling demo", cal_id="schedulingtestcalendar%i" % i)
    for (p, i) in zip(principals, range(0,len(principals)))]

## Let's start with building some icalendar event.  A meeting some
## years from now, building it using the icalendar library.
caldata = Calendar()
caldata.add('prodid', '-//tobixen//python-icalendar//en_DK')
caldata.add('version', '2.0')

uid = uuid.uuid1()
event=Event()
event.add('dtstamp', datetime.now())
event.add('dtstart', datetime.now() + timedelta(days=4000))
event.add('dtend', datetime.now() + timedelta(days=4000, hours=1))
event.add('uid', uid)
event.add('summary', 'Some test event made to test scheduling in the caldav library')
caldata.add_component(event)

## print to stdout
print("Here is our test event:")
print(caldata.to_ical().decode('utf-8'))

## that event is without any scheduling information.  If saved to the
## calendar, it will only be stored locally, no invitations sent.

## There are two ways to send calendar invites:

## * Add Attendee-lines and an Organizer-line to the event data, and
##   then use calendar.save_event(caldata) ... see RFC6638, appendix B.1
##   for an example.

## * Use convenience-method calendar.send_invites(caldata, attendees).
##   It will fetch organizer from the principal object.  Method should
##   accept different kind of attendees: strings, VCalAddress, (cn,
##   email)-tuple and principal object.

## In the example below, I'm inviting myself (by VCalAddress), test
## user #2 (by CN/email tuple) and test user #3 (by principle object.
## Keep in mind that the sender of the invitation, user #1, should not
## have access to principals[2], so it's doing a detour to find the
## principal object of user #3.
demo_calendars[0].send_meeting_request(cal, attendees=(
    principals[0].get_vcal_address()
    ('Test User 2', 't-caldav-test2@tobixen.no'),
    clients[0].principal(url=pricipals[0].url.replace('testuser1', 'testuser2'))
))

## Invite shipped.  Testuser2 should now respond to it.
for inbox_item in principal[1].schedule_inbox.get_items():
    ## an inbox_item is an ordinary CalendarResourceObject/Event/Todo etc.
    ## is_invite() will be implemented on the base class and will yield True
    ## for scheduling invite messages.
    if inbox_item.is_invite():
        
        ## Ref RFC6638, example B.3 ... to respond to an invite, it's
        ## needed to edit the ical data, find the correct
        ## "attendee"-field, change the attendee "partstat", put the
        ## ical object back to the server.  In addition one has to
        ## look out for race conflicts and retry the whole operation
        ## in case of race conflicts.  Editing ical data is a bit
        ## outside the scope of the CalDAV client library, but ... the
        ## library clearly needs convenience methods to deal with this.

        ## Invite objects will have methods accept_invite(),
        ## reject_invite(),
        ## tentative_accept_invite().  .delete() is also an option
        ## (ref RFC6638, example B.2)
        inbox_item.accept_invite()

## Testuser3 is unavailable
for inbox_item in principal[2].schedule_inbox.get_items():
    if inbox_item.is_invite():
        inbox_item.reject_invite()

## Testuser0 will have an update on the participant status in the
## inbox (or perhaps two updates?)  If I've understood the standard
## correctly, testuser0 should not get an invite and should not have
## to respond to it, but just in case we'll accept it.  As far as I've
## understood, deleting the ical objects in the inbox should be
## harmless, it should still exist on the organizers calendar.
## (Example B.4 in RFC6638)
for inbox_item in principal[0].schedule_inbox.get_items():
    if inbox_item.is_invite():
        inbox_item.accept_invite()
    elif inbox_item.is_reply():
        inbox_item.delete()

## RFC6638/RFC5546 allows an organizer to check the freebusy status of
## multiple principals identified by email address.  It's covered in
## section 4.3.2. in RFC5546 and chapter 5 / example B.5 in RFC6638.
## Most of the logic is on the icalendar format (covered in RFC5546),
## and is a bit outside the scope of the caldav client library.
## However, I will probably make a convenience method for doing the
## query, and leaving the parsing of the returned icalendar data to
## the user of the library:
some_ical_returned = principal[0].freebusy_request(
    start_time=datetime.now() + timedelta(days=3999),
    end_time=datetime.now() + timedelta(days=4001),
    participants=[
        ('Test User 2', 't-caldav-test2@tobixen.no'),
        ('Test User 3', 't-caldav-test3@tobixen.no')])

## Examples in RFC6638 goes on to describing how to accept and decline
## particular instances of a recurring events, and RFC5546 has a lot
## of extra information, like ways for a participant to signal back
## new suggestions for the meeting time, delegations, cancelling of
## events and whatnot.  It is possible to use the library for such
## things by saving appropriate icalendar data to the outbox and
## reading things from the inbox, but as for now there aren't any
## planned convenience methods for covering such things.
