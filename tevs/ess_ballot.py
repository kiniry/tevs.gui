# ess_ballot.py implements the interface 
# in Ballot.py for ballots following the style used in 
# Champaign County, IL
# The Trachtenberg Election Verification System (TEVS)
# is copyright 2009, 2010 by Mitch Trachtenberg 
# and is licensed under the GNU General Public License version 2.
# (see LICENSE file for details.)
"""
300dpi, 3 columns
Fronts
+ target at 134,100 (1/2" x 1/3")
+ target at 2380,88 (8" x 1/3")
+ target at 2398,4114 (8" x 13 2/3")
+ target at 154,4116 (1/2" x 13 2/3")
Black timing mark at (x1,y1)=(58,216),(x2,y2)=(282,262), 1/6" high x 2/3" wide
Outer bounding box begins 318,212, horizontally 0.6" from +, .36" below
right edge 2386,206, very slightly to right of +, .36" below
Next black box begins 1/2" below start of first black box
Subsequent black boxes begin at 1/3" intervals and are 1/6" tall
Left column boxes are 1/4" wide
Second column boxes either start 1/4" after end of first, and add 1/4"
or start .3" after end of first and add 2/15" (.13") 

Back + (158,94)  (2402,102) (2398,4132)  (154,4126)
Back box (134,208) (2204,218) (2196,4072) (132, 4062)
45 degree cut mark representing half of 1/2" box at left top

Row headers and row footers aligned with top and bottom black marks,
begin 0.1" after, roughly 0.125" whitish, 1/4" black, .125" whitish

Column lines .01"

Jurisdiction white on black
Contest black on gray or black on white
Text, if black on white, appears above vote ops but may optionally appear
below last vote op set.

Vote ops start 4/30" in from column edge, extend just under .25" and .125" tall and spaced 1/3" top to top.

Reliably show at least .05" continuous dark pixels at top and bottom center
"""


import Ballot
import const
from adjust import rotator
import Image, ImageStat
import ocr
import sys
import pdb
from demo_utils import *

def elim_halftone(x):
    if x>64:
        retval = 255
    else:
        retval = 0
    return retval

def get_contests_and_votes_from(image,regionlist,croplist):
    """ given an area known to contain votes and desc text, return info

    The cropped area will contain contest descriptions and voting areas.
    Unfortunately, the contest descriptions are not indented away from
    the oval voting areas.  So...  we crop looking for white line splits,
    and then treat every line as either part of a contest or as a vote
    line, depending on whether we find a pattern of white indicating
    the line contains only an oval and a single word, YES or NO.
    """
    adj = lambda f: int(round(const.dpi * f))
    oval_offset_into_column = adj(0.14)
    oval_end_offset_into_column = adj(0.39)

    votetext_offset_into_column = oval_offset_into_column
    votetext_offset_into_column += oval_end_offset_into_column 
    votetext_offset_into_column += adj(0.02)

    half_intensity = 128
    contests = []
    contest_string = ""
    crop = image.crop(croplist)
    # indent by 1/10" to avoid edges, then crop single pixel lines,
    # finding beginning and end of zones which include dark pixels
    in_dark = False
    dark_zones = []
    dark_start = 0
    dark_end = 0
    for y in range(crop.size[1]-1):
        linecrop = crop.crop((const.dpi/10,
                              y,
                              crop.size[0] - (const.dpi/10),
                              y+1))
        linestat = ImageStat.Stat(linecrop)
        if (linestat.extrema[0][0] < half_intensity) and not in_dark:
            in_dark = True
            dark_start = y
        elif (linestat.extrema[0][0] >= half_intensity) and in_dark:
            in_dark = False
            dark_end = y
            dark_zones.append([dark_start,dark_end])
    # now check each dark zone to see if it is a vote op 
    # or if it is descriptive text; vote ops will have an oval
    # in the oval channel beginning at 0.14 and extending for .24,
    # then text beginning at .38
    contest_created = False
    for dz in dark_zones:
        zonecrop1 = crop.crop((const.dpi/10,
                                dz[0],
                                crop.size[0]-(const.dpi/10), 
                                dz[1]))
        zonecrop1.save("/tmp/zonecrop1.jpg")
        zonecrop2 = crop.crop((oval_end_offset_into_column,
                                dz[0],
                                votetext_offset_into_column, 
                                dz[1]))
        zonecrop2.save("/tmp/zonecrop2.jpg")
        zone2stat = ImageStat.Stat(zonecrop2)
        zonecrop3 = crop.crop((votetext_offset_into_column,
                                dz[0],
                                votetext_offset_into_column + const.dpi,
                                dz[1]))
        zonecrop3.save("/tmp/zonecrop3.jpg")
        zone1text = ocr.tesseract(zonecrop1)
        #print "1", zone1text
        #print "2",zone2stat.mean
        zone3text = ocr.tesseract(zonecrop3)
        #print "3", zone3text
        intensity_suggests_voteop = False
        length_suggests_voteop = False
        if zone2stat.mean[0]>244: intensity_suggests_voteop = True
        if len(zone3text)<6: length_suggests_voteop = True
        if not intensity_suggests_voteop and not length_suggests_voteop:
            # add line to contest
            contest_created = False
            contest_string += zone1text.replace("\n","//")
        elif intensity_suggests_voteop and length_suggests_voteop:
            # create contest if none created, then
            if not contest_created:
                contest_created = True
                print "Creating contest",contest_string
                regionlist.append(Ballot.Contest(croplist[0],
                                                 croplist[1]+dz[0],
                                                 croplist[2],
                                                 croplist[1]+dz[1],
                                                 0,
                                                 contest_string))
                contest_string = ""
            # add voteop to contest
            choice_string = zone3text
            print "Adding choice",choice_string
            regionlist[-1].append(
                Ballot.Choice(
                    croplist[0]+oval_offset_into_column,
                    croplist[1]+ dz[0],
                    choice_string
                    )
                )

        else:
            if contest_created:
                contest_string += zone1text.replace("\n","//")
            else:
                print "Problem determining whether contest or choice"
                print zone2stat.mean
                print zone3text
                print contest_string
    #pdb.set_trace()
    return dark_zones

def get_only_votes_from(image,croplist):
    """ given an area known to contain only votes, return info

    The cropped area will contain only voting areas.  Voting areas will
    contain ovals in the oval column.  Descriptive text to the right of
    the ovals will be assigned to each oval based on being at or below
    the oval.

    """
    choices = []
    crop = image.crop(croplist)
    return choices


class EssBallot(Ballot.DuplexBallot):
    """Class representing ESS duplex ballots.

    The file name ess_ballot.py and the class name EssBallot
    correspond to the brand entry in tevs.cfg (ess.cfg), 
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
        self.back_upper_right_plus_x = 0
        self.back_upper_right_plus_y = 0
        super(EssBallot, self).__init__(images, extensions)

    # Extenders do not need to supply even a stub flip
    # because flip in Ballot.py will print a stub message in the absence
    # of a subclass implementation
    #def flip(self, im):
    #    # not implemented for Demo
    #    print "Flip not implemented for Demo."
    #    return im
    def find_back_landmarks(self, page):
        """just dup find_front_landmarks"""
        return self.find_front_landmarks(page)

    def find_front_landmarks(self, page):
        """ess ballots have circled plus signs at the four corners

        We'll look for them at the following locations allowing 1/4" slip.
        + target at 134,100 (1/2" x 1/3")
        + target at 2380,88 (8" x 1/3")
        + target at 2398,4114 (8" x 13 2/3" (1/3" from bottom)
        + target at 154,4116 (1/2" x 13 2/3" (1/3" from bottom)
        """
        iround = lambda a: int(round(a))
        adj = lambda a: int(round(const.dpi * a))
        width = adj(0.75)
        height = adj(0.75)
        # for testing, fall back to image argument if can't get from page
        try:
            im = page.image
        except:
            im = page
        # generate ulc, urc, lrc, llc coordinate pairs
        landmarks = []
        for x,y in zip(
            # x starting points
            (adj(0.25),
             im.size[0]-adj(0.3)-width-1,
             im.size[0]-adj(0.3)-width-1,
             adj(0.25)),
            # y starting points
            (adj(0.08),
             adj(0.08),
             im.size[1]-adj(0.4)-1,
             im.size[1]-adj(0.4)-1
             )
            ):
            landmark = self.find_landmark_in_region(
                page.image,
                [x,y,x+width,y+height]
            )
            landmarks.append(landmark)
        x,y = landmarks[0][0],landmarks[0][1]
        longdiff = landmarks[3][1] - landmarks[0][1]
        shortdiff = landmarks[3][0] - landmarks[0][0]
        r = float(shortdiff)/float(longdiff)
        print landmarks
        # we depend on back landmarks being processed after front
        self.back_upper_right_plus_x = landmarks[1][0]
        self.back_upper_right_plus_y = landmarks[1][1]
        print r,x,y
        return r,x,y

    def find_landmark_in_region(self, image, croplist):
        """ given an image and a cropbox, find the circled plus """
        iround = lambda x: int(round(x))
        adj = lambda f: int(round(const.dpi * f))
        dpi = const.dpi
        full_span_inches = 0.18
        line_span_inches = 0.01
        circle_radius_inches = 0.03
        full_span_pixels = adj(full_span_inches)
        line_span_pixels = adj(line_span_inches)
        circle_radius_pixels = adj(circle_radius_inches)
        croplist[2] = min(croplist[2],image.size[0]-1)
        croplist[3] = min(croplist[3],image.size[1]-1)
        image = image.crop(croplist)
        for y in range(0,image.size[1]-full_span_pixels):
            for x in range(circle_radius_pixels, image.size[0]-circle_radius_pixels):
                if (image.getpixel((x,y))[0] < 128 
                    and image.getpixel((x-1,y))[0]>=128 
                    and image.getpixel((x+(2*line_span_pixels),y))[0]>=128):
                    if ((image.getpixel((x,y+full_span_pixels-2))[0]<128
                        or image.getpixel((x+1,y+full_span_pixels-2))[0]<128
                        or image.getpixel((x-1,y+full_span_pixels-2))[0]<128)
                        and (image.getpixel((x+(2*line_span_pixels),
                                             y+full_span_pixels - 2))[0]>=128)):
                        try:
                            hline = image.crop((x-circle_radius_pixels,
                                                y+(full_span_pixels/2)-2,
                                                x+circle_radius_pixels,
                                                y+(full_span_pixels/2)+2))
                            hlinestat = ImageStat.Stat(hline)
                            if hlinestat.mean[0]>64 and hlinestat.mean[0]<192:
                                # we need to see some extremely white pixels nearby
                                white1 = image.crop((x+line_span_pixels+1,
                                                    y+ (full_span_pixels/10),
                                                    x + (2*line_span_pixels),
                                                    y + (full_span_pixels/5)))
                                whitestat1 = ImageStat.Stat(white1)
                                white2 = image.crop((x-(2*line_span_pixels),
                                                    y+ (full_span_pixels/10),
                                                    x - 1,
                                                    y + (full_span_pixels/5)))
                                whitestat2 = ImageStat.Stat(white2)
                                if whitestat1.mean[0]>224 and whitestat2.mean[0]>224:
                                    return (x+croplist[0],
                                            y+(full_span_pixels/2)+croplist[1])
                        except:
                            pass
        # successful return will have taken place by here
        raise BallotException, "could not locate plus sign landmark at %s" % (crop,)



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
        # if front, starting point is 1/4" before plus horizontal offset,
        # and .36" below plus vertical offset
        adj = lambda a: int(round(const.dpi * a))
        front_adj_x = adj(-0.25)
        front_adj_y = adj(0.36)
        print dir(page)
        barcode,tm = timing_marks(page.image,
                                  page.xoff + front_adj_x,
                                  page.yoff + front_adj_y,
                                  const.dpi)
                                  
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

    def build_front_layout(self, page):
        print "Entering build front layout."
        return self.build_layout(page)

    def build_back_layout(self, page):
        print "Entering build back layout."
        return self.build_layout(page,back=True)

    def get_left_edge_zones(self, page, column_x):
        """ return a set of pairs, (y_value, letter) for zone starts"""
        adj = lambda f: int(round(const.dpi * f)) 
        letters = []
        left = column_x + adj(0.03)
        right = left + adj(0.03)
        im = page.image
        stripe = im.crop((left,0,right,im.size[1]-1))
        lastletter = "W"
        lastred = 255
        lastdarkest = 255
        for y in range(stripe.size[1]-(const.dpi/2)):
            crop = stripe.crop((0,y,1,y+(const.dpi/32)))
            stat = ImageStat.Stat(crop)
            red = stat.mean[0]
            darkest = stat.extrema[0][0]
            if (red < 32) and (darkest < 32) and (lastred >= 32):
                if lastletter <> "B":
                    if lastletter == "G" and letters[-1][0]>(y-adj(0.1)):
                        letters = letters[:-1]
                    letters.append((y,"B"))
                    lastletter = "B"
            elif red >= 32 and red < 240 and darkest < 224:
                if lastletter <> "G":
                    letters.append((y,"G"))
                    lastletter = "G"
            elif red >=240:
                if lastletter <> "W":
                    if lastletter == "G" and letters[-1][0]>(y-adj(0.1)):
                        letters = letters[:-1]
                    letters.append((y,"W"))
                    lastletter = "W"
            lastred = red
            lastdarkest = darkest
        print letters
        return letters

    def get_middle_zones(self, page, column_x):
        """ return a set of pairs, (y_value, letter) for zone starts"""
        adj = lambda f: int(round(const.dpi * f))
        letters = []
        left = column_x
        right = left + adj(0.5)
        im = page.image
        stripe = im.crop((left,0,right,im.size[1]-1))
        lastletter = "W"
        lastred = 255
        lastdarkest = 255
        for y in range(stripe.size[1]-(const.dpi/2)):
            crop = stripe.crop((0,y,1,y+(const.dpi/4)))
            stat = ImageStat.Stat(crop)
            red = stat.mean[0]
            darkest = stat.extrema[0][0]
            if (darkest < 128) and lastletter == "W":
                letters.append((y+(const.dpi/4),"B"))
                lastletter = "B"
            elif (darkest >= 128) and lastletter == "B":
                letters.append((y,"W"))
                lastletter = "W"
        return letters

    def generate_transition_list_from_zones(self,image,regionlist,column_bounds,left,middle):
        """ given the pair of zone lists, generate a comprehensive list"""
        print left
        print middle
        """
        We should then be able to merge these sets of split information:
        anything where we find solid black or halftone is a definite break
        which may be followed either by another black or halftone area, by
        a description area, or by a vote area.
        """
        ccontest = "No current contest"
        cjurisdiction = "No current jurisdiction"
        next_white_is_votearea = False
        this_white_is_votearea = False
        next_white_is_yesno = False
        this_white_is_yesno = False
        for n in range(len(left)):
            this_white_is_votearea = False
            if next_white_is_votearea == True:
                this_white_is_votearea = True
                next_white_is_votearea = False
            this_white_is_yesno = False
            if next_white_is_yesno == True:
                this_white_is_yesno = True
                next_white_is_yesno = False
            this_y = left[n][0]
            rel_start = left[n][0] - (const.dpi/10)
            try:
                next_zone = left[n+1]
            except IndexError:
                next_zone = [0,'X']
            next_y = next_zone[0]
            rel_end = next_y - (const.dpi/10)
            if left[n][1]=='B':
                print "Black zone at %d to %d %s" % (this_y,next_y,next_zone)
                # if it's a legitimate black zone and the next zone is white,
                # that white zone is a Yes/No Vote Area (or empty)
                if (next_y - this_y) > (const.dpi/4):
                    next_white_is_yesno = True
                    # this zone becomes the current Jurisdiction
                    crop = image.crop((column_bounds[0],
                                       this_y,
                                       column_bounds[1],
                                       next_y))
                    cjurisdiction = ocr.tesseract(crop)
                    print "Jurisdiction",cjurisdiction
                    cjurisdiction = ocr.clean_ocr_text(cjurisdiction)
                    print "Cleaned Jurisdiction",cjurisdiction
                    # and the current contest is set 
                    # from the descriptive text
                    # at the start of the Yes No Vote area
            if left[n][1]=='G':
                print "Gray zone at %d to %d %s" % (this_y,next_y,next_zone)
                # if it's a legitimage gray zone and the next zone is white,
                # that white zone is a voting area (or empty)
                if (next_y - this_y) > (const.dpi/2):
                    next_white_is_votearea = True
                    crop = image.crop((column_bounds[0],
                                       this_y,
                                       column_bounds[1],
                                       next_y))
                    crop = Image.eval(crop,elim_halftone)
                    ccontest = ocr.tesseract(crop)
                    print "Contest",ccontest.replace("\n","//")
                    ccontest = ocr.clean_ocr_text(ccontest)
                    print "Cleaned Contest",ccontest
                    regionlist.append(
                        Ballot.Contest(column_bounds[0],
                                       this_y,
                                       column_bounds[1],
                                       this_y+next_y,
                                       0,
                                       ccontest)
                        )
                    

            if left[n][1]=='W':
                if this_white_is_votearea:
                    # no descriptive text anticipated
                    print "Search Vote area"
                    get_only_votes_from(image,
                                        (column_bounds[0],
                                         this_y,
                                         column_bounds[1],
                                         next_y))
                if this_white_is_yesno:
                    # descriptive text sets current contest,
                    # votes are in stretches where the middle is white
                    print "Search YesNo Vote area"
                    get_contests_and_votes_from(image,
                                                regionlist,
                                                (column_bounds[0],
                                                 this_y,
                                                 column_bounds[1],
                                                 next_y))
                print "White zone at %d to %d %s" % (this_y,next_y,next_zone)
            #relevant = filter(lambda x: x[0]>=rel_start and x[0]<=rel_end,middle)
        return regionlist

    def build_layout(self, page, back=False):
        """ get layout and ocr information from ess ballot
    The column markers represent the vote oval x offsets.
    The columns actually begin .14" before.
    We search the strip between the column edge and the vote ovals,
    looking for intensity changes that represent region breaks
    such as Jurisdiction and Contest changes.

    Unfortunately, there may be a full-ballot-width column at the top,
    containing instructions.  Random text in the instructions will trigger
    various false region breaks.

    More unfortunately, there is an inconsistency in the way jurisdictions
    and contests are handled.  (It looks good to humans.)

    Contests may begin with a black text on grey header (generally 
    following Jurisdictions as white text on black.  Contests with only
    Yes and No choices begin with black text on white background, and
    may precede either a white text on black zone OR another contest.

    The contest titles are hard to differentiate from contest descriptions,
    which can be lengthy.

    Finally, contest descriptions can continue BELOW the voting area
    of the contest.

    We make one necessary assumption, and that is that the vote area in
    such YES/NO contests will have text extending no more than halfway
    into the column, while any text will extend, except for its last line,
    more than halfway into the column.

    We'll take a vertical stripe beginning at the column center and
    of width 1/2", and look for the presence of black or gray pixels 
    in zones 1/4" tall, enough to span one and a half text lines.
    This should allow us to capture continuous vertical stretches of text
    without repeatedly finding "text", "no text".

    We'll take another vertical stripe at the very start of the column,
    from .03" for .03".  This is the extreme margin, and should allow us
    to capture zones with black headlines and grey backgrounds.  Halftoned
    areas are tricky -- they may contain no pixels more than half dark.

    We'll test for pixels of 224 or below, and an average intensity over
    a block of 240 or below.

    We should then be able to merge these sets of split information:
    anything where we find solid black or halftone is a definite break
    which may be followed either by another black or halftone area, by
    a description area, or by a vote area.

    Black, gray, and white zones are located by reading the thin margin strip.
    They must be stored in such a way that there preceding zone color is
    also available.  If the preceding zone color is gray, the white zone
    is a Vote zone.  If the preceding color zone is black, the white zone
    will contain Descriptions and YesNoVote zones.
    White zones can be analyzed by the thick center strip, combined
    with the last reading.  Where the white zone follows gray 
    center strip has text, the white zone is a Description, where the
    center strip has no text, the white zone is a YesNoVote zone.

    The five types of zones (Black, Desc, Vote1, YesNoVote, Gray) will have the
    following possible sequences.

    B -> G,D,V (capture black as Jurisdiction AND Contest)

    G -> D,V (capture G as Contest)

    D -> V,Y,B (capture D as Contest)
           
    V -> B,D (capture V as sequence of votes for current Contest)
    
    Y -> B,D (capture Y as sequence of votes for current Contest)

    When we find a vote area, it will be followed by a black or gray 
    divider or by a new description area.

    Description areas may likewise be followed by vote areas or black or gray.

    in unbroken regions, any areas with their right halves empty 
    will be presumed to represent either blank areas or voting locations.

        """
        adj = lambda f: int(round(const.dpi * f))
        oval_offset_into_column = adj(0.14)
        print "Entering build_layout."

        regionlist = []
        n = 0
        # column_markers returns a location 0.14" into the column
        ref_pt = [0,0]
        ref_pt[0] = page.xoff + adj(-0.25)
        ref_pt[1] = page.yoff + adj(0.36)
        if back:
            ref_pt[0] = self.back_upper_right_plus_x
            ref_pt[1] = self.back_upper_right_plus_y + adj(0.36)
            print "BACK"
        print ref_pt
        columns = column_markers(page.image,ref_pt)
        try:
            column_width = columns[1][0] - columns[0][0]
        except IndexError:
            column_width = im.size[0] - const.dpi
        regionlist = []
        for cnum, column in enumerate(columns):
            column_x = column[0] - oval_offset_into_column
            # determine the zones at two offsets into the column
            left_edge_zones = self.get_left_edge_zones(page,column_x)
            middle_zones = self.get_middle_zones(page,column_x+(column_width/2))
            print cnum, column
            self.generate_transition_list_from_zones(
                page.image,
                regionlist,
                (column_x,
                column_x+column_width),
                left_edge_zones,
                middle_zones
                )
            """
            print "Contests for Column", cnum, "at x offset", column_x
                regionlist.append(Ballot.Contest(column, 1, 199, 5*const.dpi, 0, contest))
                for choice in choices:
                    regionlist[-1].append(Ballot.Choice(x_offset, y_offset, choice))
            """
        return regionlist

def adjust_ulc(image,left_x,top_y,max_adjust=5):
    """ brute force adjustment to locate precise b/w boundary corner"""
    target_intensity = 255
    gray50pct = 128
    gray25pct = 64
    orig_adj = max_adjust
    while max_adjust > 0 and target_intensity > gray50pct:
        max_adjust -= 1
        left_target_intensity = image.getpixel((left_x-2,top_y))[0]
        target_intensity = image.getpixel((left_x,top_y))[0]
        right_target_intensity = image.getpixel((left_x+2,top_y))[0]
        above_target_intensity = image.getpixel((left_x,top_y-2))[0]
        above_right_target_intensity = image.getpixel((left_x+2,top_y-2))[0]
        above_left_target_intensity = image.getpixel((left_x-2,top_y-2))[0]
        below_target_intensity = image.getpixel((left_x,top_y+2))[0]
        below_left_target_intensity = image.getpixel((left_x-2,top_y+2))[0]
        below_right_target_intensity = image.getpixel((left_x+2,top_y+2))[0]
        #print above_left_target_intensity,above_target_intensity,above_right_target_intensity
        #print left_target_intensity,target_intensity,right_target_intensity
        #print below_left_target_intensity,below_target_intensity,below_right_target_intensity
        changed = False
        if below_target_intensity > gray25pct and target_intensity > gray25pct:
            left_x += 2
            changed = True
        elif below_left_target_intensity <= gray50pct:
            left_x -= 2
            changed = True
        if right_target_intensity > gray25pct and target_intensity > gray25pct:
            top_y += 2
            changed = True
        elif above_right_target_intensity <= 127:
            top_y -= 2
            changed = True
        if not changed:
            break
    if max_adjust == 0 and changed == True:
        e = "could not fine adj edge at (%d, %d) after %d moves" % (left_x,
                                                                    top_y,
                                                                    orig_adj)
        raise Ballot.BallotException, e
    return (left_x,top_y)

def timing_marks(image,x,y,dpi=300):
    """locate timing marks and code, starting from closest to ulc symbol"""
    # go out from + towards left edge by 1/8", whichever is closer
    # down from + target to first dark, then left to first white
    # and right to last white, allowing a pixel of "tilt"

    adj = lambda f: int(round(const.dpi * f))

    retlist = []
    half = adj(0.5)
    third = adj(0.33)
    qtr = adj(0.25)
    down = adj(0.33)
    sixth = adj(0.167)
    twelfth = adj(0.083)
    gray50pct = 128

    left_x = x
    top_y = y
    retlist.append( (left_x,top_y) )
    # now go down 1/2" and find next ulc, checking for drift
    top_y += half
    for n in range(adj(0.1)):
        pix = image.getpixel((left_x+adj(0.1),top_y + n))
        if pix[0] > 128:
            top_y = top_y + 1
    code_string = ""
    zero_block_count = 0
    while True:
        if top_y > (image.size[1] - const.dpi):
            break
        (left_x,top_y) = adjust_ulc(image,left_x,top_y)
        # check for large or small block to side of timing mark
        block = block_type(image,qtr,left_x+half,top_y+twelfth)
        if block==0: 
            zero_block_count += 1
        elif block==1:
            code_string = "%s%dA" % (code_string,zero_block_count)
            zero_block_count = 0
        elif block==2:
            code_string = "%s%dB" % (code_string,zero_block_count)
            zero_block_count = 0
            
        retlist.append((left_x,top_y))
        # now go down repeated 1/3" and find next ulc's until miss
        top_y += third
    # try finding the last at 1/2" top to top
    left_x = retlist[-1][0]
    top_y = retlist[-1][1]
    top_y += half
    (left_x,top_y) = adjust_ulc(image,left_x,top_y)
    retlist.append((left_x,top_y))
    
    return (code_string, retlist)

def block_type(image,pixtocheck,x,y):
    """check pixcount pix starting at x,y; return code from avg intensity"""
    intensity = 0
    for testx in range(x,x+pixtocheck):
        intensity += image.getpixel((testx,y))[0]
    intensity = intensity/pixtocheck
    if intensity > 192:
        retval = 0
    elif intensity > 64:
        retval = 1
    else:
        retval = 2
    return retval


def column_markers(image,ref_pt,min_runlength_inches=.2,zonelength_inches=.25):
    """given first timing mark, find column x offsets by inspecting boxes

    The uppermost timing mark is vertically aligned with a box containing
    column headers.  This column header box is approximately 1/6" tall.
    
    We go halfway down into the column header box, looking for .24" 
    black rectangles which are spaced .14 inches from vertical lines 
    left and right; these represent the x offsets of vote opportunities.  

    The actual test is for runs of pixels of red intensity < 128.  
    The run must have only one miss for min_runlength_inches
    in a horizontal strip one pixel high.

    If the timing mark is in the left ballot half, we search rightwards;
    else, we search leftwards.
    """
    adj = lambda f: int(round(const.dpi * f))
    columns = []
    top_y = ref_pt[1]
    first_x = ref_pt[0]

    twelfth = adj(0.083)
    min_runlength = adj(min_runlength_inches)
    true_pixel_width_of_votezone = adj(zonelength_inches)
    # go in 1" from edge, 
    # follow top line across, adjusting y as necessary, 
    black_run_misses = 0
    black_runlength = 0
    if first_x > (image.size[0]/2):
        run_backwards = True
        startx = first_x - const.dpi
        endx = const.dpi/4
        incrementx = -1
    else:
        run_backwards = False
        startx = first_x + const.dpi
        endx = image.size[0] - const.dpi
        incrementx = 1

    # start by scanning downwards until you pick up the line
    counter = 0
    while True:
        pix = image.getpixel((startx,top_y))
        if pix[0]<64: break
        top_y += 1
        counter += 1
        if counter > (const.dpi/10):
            raise Ballot.BallotException, "couldn't find line atop columns"

    for x in range(startx,endx,incrementx):
        # if we lose the line,
        if image.getpixel((x,top_y))[0]>64:
            # go up or down looking for black pixel
            if image.getpixel((x,top_y-1))[0]<image.getpixel((x,top_y+1))[0]:
                top_y -= 1
            else:
                top_y += 1
        if image.getpixel((x,top_y+twelfth))[0] < 128:
            black_runlength += 1
            if black_runlength >= min_runlength:
                if run_backwards:
                    # instead of subtracting min_runlength
                    # subtract true_pixel_width_of_votezone
                    # to establish actual minimum x of votezone
                    columns.append((x+min_runlength-true_pixel_width_of_votezone,top_y))
                else:
                    columns.append((x-black_runlength,top_y))
                black_runlength = 0
                black_run_misses = 0
        else:
            black_run_misses += 1
            if black_run_misses > 1:
                black_runlength = 0    
                black_run_misses = 0

    if run_backwards:
        columns.reverse()
    return columns
    # looking 1/12" down for quarter inches of black

def get_marker_offset(tm_markers,height):
    """how far has the timing mark at this height been offset from top_x"""
    xoffset = 0
    for tm_marker in tm_markers:
        if tm_marker[1]>height:
            xoffset = tm_marker[0] - tm_markers[0][0]
            break
    return xoffset

