from ivlemods.database import db_session, init_db

init_db()

from ivlemods.models import Job, User

db_session.add_all([
#    User('a0071932', 'a0071932@nus.edu.sg', 'LUO KENN SIANG',
#        '3CD054880A5F2D678947FE374FC9D58011DF144BA23A2B1D57CA572F65C499DA25BA9BBC6F8567C09489150E5BA4DC849345256A90D668169DF61ACC3228C5BE601C82579306C44436981FDA58604FC2EED139284829DB9630A9B43235AAA0667AD545A371A415438236B0F90BC2D5D83D819DD3C96C2632425D0C41F5FB56DB15B8F140CCD44478EAF5BEF4ECAD8F90DB6C67689DEB1D4BC2E0E94D70A914D7B2BF6BCFD7D5B4623C8B8B9A431B4CCF92D1EEDE709967484417920B001908619119EC25772499CF44C367F55C35918E',
#        'vsmy2884o7xcejs', 'uamfn7dl2feyob5'),
    User('u0906931', 'u0906931@nus.edu.sg', 'EU BENG HEE',
        '5CB87FF2665DB3E789F3ABD7F95E02447A958AB8EC3FFDC344042FAD0C98A3ED7C7FC97B509E242F83402D3C39DDDB9562BFDF593C4BF9F731F7063C57F9131ECC54AED0F885FBEC919A8A4C66BDF3B7F5B323E6294E867E677BA6C44369F82A9807F12FEA399A4140881502F24B5CDBAB091355B1E0650FC89407B76EFF6EDBC5129C4F6E186AE7BDC33A42B68914C8CFB55D91CCBDB5056EAFAD90223A880B22074CF24326EFA6171EDB25CDC4ADA4E742AF50CBFEE931B947184496B307B8C4BBD8F4553AFF2C8241F74867777216',
        'f2gexq93y53c8ee','a79mkigj2re1639'),
#    Job('1000', 'http://www.ics.uci.edu/~bic/courses/JaverOS/pr3.pdf', 'http',
#        1, 'CS2106/pr3.pdf'),
#    Job('1001',
#        'http://ics.uci.edu/~bic/courses/OS-2012/Lectures-on-line/proj3.pptx',
#        'http', '1', 'CS2106/proj3.pptx'),
#    Job('1000', 'http://www.ics.uci.edu/~bic/courses/JaverOS/pr3.pdf', 'http',
#        '1', 'CS2106/hello.pdf')
])
db_session.commit()