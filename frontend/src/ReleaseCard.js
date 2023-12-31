import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardMedia from '@mui/material/CardMedia';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';


export default function ReleaseCard({release, releaseType}) {
    return (
        <Link href={`/${releaseType}s/${release.id}`} underline="none">
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardMedia
                component="div"
                sx={{
                    // 16:9
                    pt: '56.25%',
                }}
                image={release.cover_image || 'https://wallpapers.com/images/featured/music-notes-zpmz2slc377qu3wd.jpg'}
                />
                <CardContent sx={{ flexGrow: 1 }}>
                <Typography gutterBottom variant="h5" component="h2">
                    {release.title}
                </Typography>
                <Typography>
                    {Object.entries(release.artists_usernames).map(([artistId, username], index, array) => (
                    <React.Fragment key={artistId}>
                        <Link href={`/users/${artistId}/`} variant="body2">
                            {username}
                        </Link>
                        {index < array.length - 1 && ', '}
                    </React.Fragment>
                    ))}
                </Typography>
                </CardContent>
            </Card>
        </Link>
    );
}