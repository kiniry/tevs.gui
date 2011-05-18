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
import sys
import pdb
from demo_utils import *

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
        super(EssBallot, self).__init__(images, extensions)

    # Extenders do not need to supply even a stub flip
    # because flip in Ballot.py will print a stub message in the absence
    # of a subclass implementation
    #def flip(self, im):
    #    # not implemented for Demo
    #    print "Flip not implemented for Demo."
    #    return im

    
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
        return self.build_layout(page)

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
        pdb.set_trace()
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

    def generate_transition_list_from_zones(self,left,middle):
        """ given the pair of zone lists, generate a comprehensive list"""
        print left
        print middle
        pass
    def build_contests(self,tlist):
        """ given the comprehensive list of transitions, generate contests"""
        print left
        print middle
        pass

    def build_layout(self, page):
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
        landmark = [0,0]
        landmark[0] = page.xoff + adj(-0.25)
        landmark[1] = page.yoff + adj(0.36)

        print landmark
        columns = column_markers(page.image,landmark,const.dpi)
        try:
            column_width = columns[1][0] - columns[0][0]
        except IndexError:
            column_width = im.size[0] - const.dpi
        for cnum, column in enumerate(columns):
            column_x = column[0] - oval_offset_into_column
            # determine the zones at two offsets into the column
            left_edge_zones = self.get_left_edge_zones(page,column_x)
            middle_zones = self.get_middle_zones(page,column_x+(column_width/2))
            tlist = self.generate_transition_list_from_zones(
                left_edge_zones,
                middle_zones
                )
            regionlist = self.build_contests(page,tlist)
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


def column_markers(image,tm_marker,dpi,min_runlength_inches=.2,zonelength_inches=.25):
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
    top_y = tm_marker[1]
    first_x = tm_marker[0]

    twelfth = adj(0.083)
    min_runlength = adj(min_runlength_inches)
    true_pixel_width_of_votezone = adj(zonelength_inches)
    # go in 1" from edge, 
    # follow top line across, adjusting y as necessary, 
    black_run_misses = 0
    black_runlength = 0
    if first_x > (image.size[0]/2):
        run_backwards = True
        startx = first_x - dpi
        endx = dpi/2
        incrementx = -1
    else:
        run_backwards = False
        startx = first_x+dpi
        endx = image.size[0]-dpi
        incrementx = 1
        
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

def column_dividers(image, top_x, tm_markers,dpi=300,stop=True):
    """take narrow strip at start of column and return intensity changes

    """
    adj = lambda f: int(round(const.dpi * f))
    print "Column dividers for column w/ top_x = ",top_x
    changelist = []
    line_to_oval = adj(.14)
    pixels_to_backup_to_zone_start = ((line_to_oval * 2) / 3)
    pixels_to_backup_to_zone_end = ((line_to_oval * 1) / 3)
    fiftieth = adj(0.02)
    twelfth = adj(0.083)
    # for each column, generate a list of crops
    # at x,y+twelfth,x+.02",y+twelfth+.02" every marker, adjusting x based
    # on any change in x in the tm_markers
    first_xdist = top_x - tm_markers[0][0]
    lastintensity = 255
    lastshade = "W"
    # don't capture changes until you enter your first black zone
    skip = True
    for marker in tm_markers:
        marker_adj = marker[0] - tm_markers[0][0]
        #print marker, marker_adj
        y = marker[1]
        croplist = (top_x+marker_adj-pixels_to_backup_to_zone_start,
                    y+twelfth,
                    top_x+marker_adj-pixels_to_backup_to_zone_end,
                    y+twelfth+fiftieth)
        #print "Crop",croplist,
        crop = image.crop(croplist)
        s = ImageStat.Stat(crop)
        intensity = int(round(s.mean[0]))
        # capture changes once you enter a black zone
        if intensity < 64: skip = False
        #print intensity, s.mean[0], s.mean[1], s.mean[2]
        if (intensity > 64 and intensity < 224): shade = "G"
        elif (intensity >= 224): shade = "W"
        else: shade = "B"
        if (shade <> lastshade):
            if not skip:
                # the actual transition starts approx 1/12" above 
                # the start of each timing mark
                changelist.append((y-twelfth,shade))
        lastintensity = intensity
        lastshade = shade

    # list is now constructed, but some entries need to be split
    #some white regions will include blocks of text
    #in addition to the vote ops.
    #Try to find a white vertical strip starting at the bottom
    #and after the column marker's x offset; if this strip
    #goes all the way up, it's all vote ops, otherwise you've
    #got some sort of text at the top (or, worse, the middle)
    #print "Changelist:",changelist
    split1list = []
    for n in range(len(changelist)):
        split1list.append(changelist[n])
        if changelist[n][1] <> "W":
            #print top_x,changelist[n]
            continue
        else:
            # this has been modified to deal with T/W/T/W/T/W
            # why is Jurisdiction CHAMPAIGN COUNTY on 00000002.jpg 
            # not picking up its one contest?  find out next.
            if n == (len(changelist)-1):
                bottom_y = image.size[1] - onethird
            else:
                top_y = changelist[n][0]
                bottom_y = changelist[n+1][0]
            zone_height = dpi/16#!!! changed from dpi/16
            # adjust top_x based on tilt and how far down we are
            #print top_x+(0.3*dpi), top_x+(0.4*dpi)
            #pdb.set_trace()
            marker_offset = get_marker_offset(tm_markers,(changelist[n][0]+bottom_y)/2)
            print "Marker offset",marker_offset
            #pdb.set_trace()
            zones = white_stripes_height_zones(image,
                                               dpi,
                                               zone_height,
                                               marker_offset + top_x + (0.3*dpi),
                                               changelist[n][0]-twelfth,
                                               bottom_y-twelfth)
            cumulative = 0
            print top_x, changelist[n],zones
            #pdb.set_trace()
            """
            When zones contains a sequence of more than 2 contig of one shade
            followed by more than 2 contig of the other, it must be split at the
            transition, with the dark zone treated as "T/ext" and the light
            zone treated as "W/hite"; ignore any switch in the last two
            zones, because a late switch is just the end of the White region
            """
            lastz = "X"
            contig = 0
            cumulative = 0
            split = False
            split2list = []
            # ignore the bottom four slices (at 1/16", the bottom 1/4")
            for z in zones[:-4]:
                if (z == 'D' and lastz == 'W') or (z == 'W' and lastz == 'D'):
                    if contig > 4:
                        #print
                        #print "split_here at",lastz,"to",z
                        split2list.append((changelist[n][0]+(cumulative*zone_height),z))
                        split = True
                        contig = 0
                elif z == lastz:
                    contig = contig + 1
                lastz = z
                cumulative += 1                           
                #print z,
            #print
            # if split, we alter the last entry in split1list to flavor "D"
            # and append everything in split2list
            # if not split, we leave the last entry in split1list alone
            if split:
                lasty = split1list[-1][0]
                #print "Removing",split1list[-1]
                split1list = split1list[:-1]
                split1list.append((lasty,'D'))
                #print "Appending",split1list[-1]
                for item in split2list:
                    #print "Appending",item
                    split1list.append(item)
    # Whites should be further split into zones
    # corresponding to single vote opportunities
    # by splitting at horizontal white gaps and confirming
    # existence of filled or empty oval at left and text at right
    outlist = []
    for n in range(len(split1list)):
        outlist.append(split1list[n])
        if split1list[n][1] <> "W":
            continue
        try:
            white_ys = []
            last_white_y = 0
            last_dark_y = 0

            for y in range(split1list[n][0],split1list[n+1][0]):
                all_white = True
                for x in range(top_x - int(0.1 * dpi), top_x + dpi):
                    if image.getpixel((x,y))[0]<128:
                        all_white = False
                if all_white:
                    if last_white_y <> (y - 1):
                        white_ys.append([y,y])
                    last_white_y = y
                else:
                    if last_dark_y <> (y - 1) and (last_dark_y <> 0):
                        white_ys[-1][1]=y-1
                    last_dark_y = y
                pass

            #if top_x > 500 and split1list[n][0] >3200: 
            #    print split1list[n][0], split1list[n+1][0]
            #    print white_ys
            #    pdb.set_trace()

            first = True
            for white in white_ys:
                if (((white[1] - white[0]) > twelfth)
                    and (white[1] < (split1list[n+1][0]-(dpi/10)))):
                    outlist.append((white[1]-3,"W"))
            #print "Outlist",outlist
        except IndexError:
            pass
                           

    # return list of sharp intensity changes, starting with black
    #print outlist

    return outlist

def white_stripes_height_zones(im,dpi,height,x1,y1,y2):
    # from the lowest y to the highest, for 1/10" from x1
    # search for zones of 1/8" with and without dark pixels;
    # return list of dark/white...
    # of first such encounter
    retval = ""
    black_count = 0
    contig_lines_no_black = 0
    for y in range(y2-3,y1,-height):
        crop = im.crop((x1,y-height,x1+(dpi/10),y)) 
        stat = ImageStat.Stat(crop)
        if stat.extrema[0][0] < 192:
            retval = "D%s" % (retval,)
        else:
            # check an inch beyond to confirm zone is truly white
            crop2 = im.crop((x1,y-height,x1+dpi,y)) 
            stat2 = ImageStat.Stat(crop)
            if stat2.extrema[0][0]>=192:
                retval = "W%s" % (retval,)
    return retval
class BallotRegion(object):
    JURISDICTION = 1
    CONTEST = 2
    PROP = 3
    TEXT = 4
    CHOICE = 5

    def __init__(self,flavor,x1,y1,x2,y2,vop_x=0,vop_y=0,text=""):
        self.flavor = flavor
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.vop_x = vop_x
        self.vop_y = vop_y
        self.bbox = (self.x1,self.y1,self.x2,self.y2)
        self.text = text
        self.purpose = "?"
        # set purpose based on flavor
        if self.flavor=='B':
            self.purpose = BallotRegion.JURISDICTION
        elif self.flavor=='G':
            self.purpose = BallotRegion.CONTEST
        # "D" split out from a white region as a dark area
        elif self.flavor=='D':
            self.purpose = BallotRegion.CONTEST
        elif self.flavor=='T':
            self.purpose = BallotRegion.TEXT
        elif self.flavor=='W':
            self.purpose = BallotRegion.CHOICE
        
    def croplist(self):
        return (self.x1,self.y1,self.x2,self.y2)


def build_regions(im,top_columns,tm_list,dpi,stop=True,verbose=False):
    regionlist = []
    onethird = int(round(dpi/3.))
    twelfth = int(round(dpi/12.))
    guard_twentieth = int(round(dpi/20.))
    guard_tenth = int(round(dpi/10.))
    guard_fifth = int(round(dpi/5.))
    cropnum = 0
    for top_xy in top_columns:
        dividers = column_dividers(im,top_xy[0],tm_list,dpi,stop)
        #print top_xy,dividers
        for n in range(len(dividers)):
            flavor = dividers[n][1]
            if verbose and top_xy[0] > 500 and dividers[n][0] >3200: 
                print top_xy, dividers
                print n,dividers[n]

            # only flavor "W" will have vote ops
            # flavors may be W/hite, B/lack, G/ray, or T/extonlywhite or D/ark
            if flavor == "W":
                indent = onethird
            else:
                indent = -(dpi/10)
            # for the last entry in dividers, crop to bottom
            # for earlier entries, crop to next divider
            if n == (len(dividers)-1):
                bottom = im.size[1]-(dpi/3)
            else:
                bottom = dividers[n+1][0]

            # skip anything within a third of an inch of the bottom
            if bottom > (im.size[1] - (dpi/3)): 
                continue

            # skip anything where bottom is <= top
            if bottom <= (dividers[n][0]-twelfth): 
                print "Dividers[n]",dividers[n]
                print "Bottom",bottom
                print "Bottom less than dividers[n][0] - twelfth"
                pdb.set_trace()
                continue

            btregion = BallotRegion(flavor,
                                    top_xy[0]+indent,
                                    dividers[n][0]-twelfth, #backup to pick up top of first line if necessary
                                    top_xy[0]+(column_width-indent)-onethird,
                                    bottom-twelfth ) # backup to lose top of next segment
            # if you are creating a ballot region containing a vote op
            # find the vote op and set the region's vop_x and vop_y
            if flavor == "W":
                vop_x = top_xy[0]
                btregion.vop_x = top_xy[0]
                # having set the templates vop_x, 
                # let's adjust OUR vop_x for tilt
                marker_adjust = get_marker_offset(tm_list,dividers[n][0])
                #print marker_adjust, vop_x,marker_adjust+vop_x
                #if dividers[n][0]>2400:
                #    pdb.set_trace()
                for vop_y in range(dividers[n][0] - twelfth,dividers[n][0]+(dpi/3)):
                    #if vop_y == 2471:
                    #    pdb.set_trace()
                    pix1 = im.getpixel((marker_adjust+vop_x+(dpi/8),vop_y))[0]
                    pix2 = im.getpixel((marker_adjust+vop_x+(dpi/8),vop_y+(dpi/10)))[0]
                    pix3 = im.getpixel((marker_adjust+vop_x+(dpi/8),vop_y-1+(dpi/10)))[0]
                    pix4 = im.getpixel((marker_adjust+vop_x+(dpi/8),vop_y+1+(dpi/10)))[0]
                    pix5 = im.getpixel((marker_adjust+vop_x+(dpi/8),vop_y-2+(dpi/10)))[0]
                    pix6 = im.getpixel((marker_adjust+vop_x+(dpi/8),vop_y+2+(dpi/10)))[0]
                    # above left should be light
                    pix7 = im.getpixel((marker_adjust+vop_x,vop_y-1))[0]
                    # below left should be light
                    pix8 = im.getpixel((marker_adjust+vop_x,vop_y+(dpi/10)+2))[0]
                    if pix1 < 192 and (pix2<192 or pix3<192 or pix4<192 or pix5<192 or pix6<192) and pix7 > 192 and pix8 > 192:
                        # check to see if there's a clean line 1/10" above
                        test_y = vop_y - guard_tenth
                        clean = True
                        for test_x in range(marker_adjust+vop_x - guard_twentieth,
                                            marker_adjust+vop_x + guard_fifth):
                            pix = im.getpixel((test_x,test_y))[0]
                            if pix < 192:
                                clean = False
                                break
                        if clean:
                            btregion.vop_y = vop_y
                            break
                if btregion.vop_y == 0:
                    #pdb.set_trace()
                    print "No vote op found y to y",dividers[n][0],dividers[n][0]+dpi

            crop = btregion.croplist()
            if crop[3]<=crop[1] or crop[2]<=crop[0] or crop[3]>= im.size[1] or crop[2]>=im.size[0]:
                print "Skipping bad crop",crop
                continue
            crop = im.crop(crop)
            jpg_name = "/tmp/crops/crop%02d_%s.jpg" % (cropnum,flavor)
            tif_name = "/tmp/crops/crop%02d_%s.tif" % (cropnum,flavor)
            bare_name = "/tmp/crops/crop%02d_%s" % (cropnum,flavor)
            crop.save(jpg_name)
            arglist = ["/usr/bin/convert","-compress","None"]
            if (flavor == "G"):
                arglist.append("-threshold")
                arglist.append("35%")
            arglist.append(jpg_name)
            arglist.append(tif_name)
            p = subprocess.Popen(arglist,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE
                                 )
            errstuff = p.stderr.read()
            outstuff = p.stdout.read()
            sts = os.waitpid(p.pid,0)[1]
            if len(errstuff)>100:
                print errstuff
            p = subprocess.Popen(["/usr/local/bin/tesseract", 
                                  tif_name, 
                                  bare_name],
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE
                                 )
            errstuff = p.stderr.read()
            outstuff = p.stdout.read()
            sts = os.waitpid(p.pid,0)[1]
            if len(errstuff)>100:
                print errstuff
            textfile = open(bare_name+".txt","r")
            
            btregion.text = textfile.read()
            textfile.close()
            os.remove(jpg_name)
            os.remove(tif_name)
            os.remove(bare_name+".txt")
            regionlist.append(btregion)
            #if stop and btregion.text.find("Champ")>-1:
            #    for x in regionlist: print x.x1,x.y1,x.text
            #    pdb.set_trace()
            cropnum += 1
    return regionlist
    # to capture black text off gray, threshold at 96/255 (empirical)
    # capture text within each intensity region that is gray or black
    # divide text where intensity region is white into individual lines
    # by splitting into 

