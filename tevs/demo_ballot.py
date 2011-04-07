# demo_ballot.py implements the interface 
# in Ballot.py, as a guide to those extending TEVS to new ballot types.
# The Trachtenberg Election Verification System (TEVS)
# is copyright 2009, 2010 by Mitch Trachtenberg 
# and is licensed under the GNU General Public License version 2.
# (see LICENSE file for details.)


import Ballot
import const
from adjust import rotator

from demo_utils import *

class DemoBallot(Ballot.Ballot):
    """Class representing demonstration ballots.

    Each demonstration ballot's layout code, and contest and choice locations
    are entered by the user through a text interface.

    Precinct code can be any number from 1 to 100.

    The file name demo_ballot.py and the class name DemoBallot
    correspond to the brand entry in tevs.cfg (demo.cfg), 
    the configuration file.
    """

    def __init__(self, images, extensions):
        #convert all our constants to locally correct values
        # many of these conversions will go to Ballot.py,
        # extenders will need to handle any new const values here, however
        adj = lambda f: int(round(const.dpi * f))
        # this is the size of the printed vote target's bounding box
        self.oval_size = (
            adj(const.oval_width_inches),
            adj(const.oval_height_inches)
        )
        # add these margins to the vote target's bounding box 
        # when cropping and analyzing for votes
        self.oval_margin = adj(.03) #XXX length should be in config or metadata
        self.min_contest_height = adj(const.minimum_contest_height_inches)
        self.vote_target_horiz_offset = adj(const.vote_target_horiz_offset_inches)
        self.writein_xoff = adj(-2.5) #XXX
        self.writein_yoff = adj(-.1)
        self.allowed_corner_black = adj(const.allowed_corner_black_inches)
        super(DemoBallot, self).__init__(images, extensions)

    # Extenders do not need to supply even a stub flip
    # because flip in Ballot.py will print a stub message in the absence
    # of a subclass implementation
    #def flip(self, im):
    #    # not implemented for Demo
    #    print "Flip not implemented for Demo."
    #    return im

    def find_landmarks(self, page):
        """ retrieve landmarks for a demo template, set tang, xref, yref

        Landmarks for the demo ballot are normally at 1/2" down and
        1" in from the top left and top right corners.

        The "image" you are using as a template may be offset or 
        tilted, in which case that information will be recorded
        so it may be taken into account when future images are
        examined.
        """
        a = ask("""Enter the x coordinate of an upper left landmark;
if your template is not offset or tilted, you could use 150.  If there's no
such landmark, enter -1:
""", int, -1)
        b = ask("""Now enter the corresponding y coordinate;
if your template is not offset or tilted, you could use 75.  If there's no
such landmark, enter -1:
""", int, -1)
        c = ask("""Enter the x coordinate of an upper RIGHT landmark;
if your template is not offset or tilted, you could use 2050.  If there's no
such landmark, enter -1:
""", int, -1)
        d = ask("""Enter the corresponding y coordinate;
if your template is not offset or tilted, you could use 75.  If there's no
such landmark, enter -1:
""", int, -1)
        if -1 in (a, b, c, d):
            raise Ballot.BallotException("Could not find landmarks")

        # flunk ballots with more than 
        # allowed_corner_black_inches of black in corner
        # to avoid dealing with severely skewed ballots

        errmsg = "Dark %s corner on %s"
        testlen = self.allowed_corner_black
        xs, ys = page.image.size

        #boxes to test
        ul = (0,             0,           
              testlen,       testlen)
 
        ur = (xs - testlen,  0,           
              xs - 1,        testlen)

        lr = (xs - testlen,  ys - testlen,
              xs - 1,        ys - 1)
 
        ll = (0,             ys - testlen,
              testlen,       ys - 1)

        for area, corner in ((ul, "upper left"),
                             (ur, "upper right"),
                             (lr, "lower right"),
                             (ll, "lower left")):
            avg_darkness = ask(
                "What's the intensity at the " + corner,
                IntIn(0, 255)
            )
            if int(avg_darkness) < 16:
                raise Ballot.BallotException(errmsg % (corner, page.filename))

        xoff = a
        yoff = b

        shortdiff = d - b
        longdiff = c - a
        rot = -shortdiff/float(longdiff)
        if abs(rot) > const.allowed_tangent:
            raise Ballot.BallotException(
                "Tilt %f of %s exceeds %f" % (rot, page.filename, const.allowed_tanget)
            )

        return rot, xoff, yoff 

    def get_layout_code(self, page):
        """ Determine the layout code by getting it from the user

        The layout code must be determined on a vendor specific basis;
        it is usually a series of dashes or a bar code at a particular
        location on the ballot.

        Layout codes may appear on both sides of the ballot, or only
        on the fronts.  If the codes appear only on the front, you can
        file the back layout under a layout code generated from the
        front's layout code.
        """
        barcode = ask("""Enter a number as the simulated barcode,
        or -1 if your ballot is missing a barcode""", IntIn(0, 100), -1)
        # If this is a back page, need different arguments
        # to timing marks call; so have failure on front test
        # trigger a back page test
        if barcode == -1:
            barcode = "BACK" + self.pages[0].barcode
        page.barcode = barcode
        return barcode

    def extract_VOP(self, page, rotate, scale, choice):
        """Extract a single oval, or writein box, from the specified ballot.
        We'll tell you the coordinates, you tell us the stats.  The
        information gathered should enable the IsVoted function to 
        make a reasonable decision about whether the area was voted,
        but the data is also available to anyone else wanting to see
        the raw statistics to make their own decision.
        """
        # choice coords should be the upper left hand corner 
        # of the bounding box of the printed vote target
        x, y = choice.coords()
        x = int(x)
        y = int(y)
        iround = lambda x: int(round(x))
        margin = iround(.03 * const.dpi)

        #XXX BEGIN move into transformer
        xoff = page.xoff - iround(page.template.xoff*scale)
        yoff = page.yoff - iround(page.template.yoff*scale)
        x, y = rotate(xoff + x, yoff + y)
        x = iround(x * scale)
        y = iround(y * scale)
        #XXX end move into transformer (which should now just take a page obj)

        ow, oh = self.oval_size
        print """At %d dpi, on a scale of 0 to 255, 
tell us the average intensity from (%d, %d) for width %d height %d, 
given an offset from the specified x of %d
""" % (const.dpi, x, y, ow, oh, self.vote_target_horiz_offset)
        intensity = ask("Intensity", IntIn(0, 255))
        lowest = ask("Lowest count", IntIn(0, 1000))
        low = ask("Low count", IntIn(0, 1000))
        high = ask("High count", IntIn(0, 1000))
        highest = ask("Highest count", IntIn(0, 1000))
        suspicious = ask("Value of suspicious", int)
        ari, agi, abi  = intensity, intensity, intensity
        lowestr, lowestg, lowestb = lowest, lowest, lowest
        lowr, lowg, lowb = low, low, low
        highestr, highestg, highestb = highest, highest, highest
        highr, highg, highb = high, high, high
        stats = Ballot.IStats(
(ari, lowestr, lowr, highr, highestr,
agi, lowestg, lowg, highg, highestg,
abi, lowestb, lowb, highb, highestb, x, y, 0)
        )

        #can be in separate func?
        cropx = stats.adjusted.x
        cropy = stats.adjusted.y
        crop = page.image.crop((
            cropx - margin,
            cropy - margin,
            cropx + margin + ow, 
            cropy + margin + oh
        ))

        #can be in separate func?
        
        voted, ambiguous = self.extensions.IsVoted(crop, stats, choice)
        writein = False
        if voted:
           writein = self.extensions.IsWriteIn(crop, stats, choice)
        if writein:
            print "Gather information about the write-in at",
            print cropx - margin, cropy - margin,
            print cropx + self.writein_xoff + margin,
            print cropy + self.writein_yoff + margin
            print "In this version, it's your responsibility to save"
            print "the write-in images; in subsequent versions they"
            print "will be saved by code in Ballot.py"

        return cropx, cropy, stats, crop, voted, writein, ambiguous

    def build_layout(self, page):
        """ get layout and ocr information from Demo ballot

        Building the layout will be the largest task for registering
        a new ballot brand which uses a different layout style.

        Here, we'll ask the user to enter column x-offsets, 
        then contests and their regions,
        and choices belonging to the contest.
        """
        print """Entering build_layout.

You will need to provide a comma separated list of column offsets,
then you will need to provide, for each column, information about
each contest in that column: its contest text, its starting y offset,
and the same for each choice in the contest.
"""
        regionlist = []
        n = 0
        columns = ask(
            """Enter the column offsets of the vote columns, separated by commas""",
            CSV(int)
        )
        for cnum, column in enumerate(columns):
            print "Contests for Column", cnum, "at x offset", column
            while True:
                contest = ask("Enter a contest name")
                choices = ask("Enter a comma separated list of choices",
                    CSV())
                # values are the x1,y1,x2,y2 of the bounding box of the contest
                # bounding box, 0 for regular contest or 1 for proposition,
                # and the text of the contest; we'll just dummy them here
                regionlist.append(Ballot.Contest(column, 1, 199, 5*const.dpi, 0, contest))
                for choice in choices:
                    x_offset = ask("Enter the x offset of the upper left hand corner \nof the printed vote target for " + choice, int)
                    y_offset = ask("Enter the y offset of the upper left hand corner \nof the printed vote target for " + choice, int)
                    # values are the x,y of the upper left corner
                    # of the printed vote opportunity, 
                    # and the text of the choice
                    #TODO add x2,y2
                    regionlist[-1].append(Ballot.Choice(x_offset, y_offset, choice))
        return regionlist

