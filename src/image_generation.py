import numpy as np
import numpy.matlib
from scipy import ndimage
import matplotlib.pyplot as plt

def seedBeadsN(pts, sizeI, sigma):
    '''
    Generate synthetic images with beads of gaussian intensity

    '''

    nPts, nDims = pts.shape
    bead_size = np.amax(np.ceil(sigma*2*5), axis=0)

    # Create grid points to compute gaussian particle intensity
    if nDims == 2:
        m = np.mgrid[0:bead_size[0], 0:bead_size[1]]
    elif nDims == 3:
        m = np.mgrid[0:bead_size[0], 0:bead_size[1], 0:bead_size[2]]
    else:
        print('Can only handle 2D or 3D image')
        return -1
    
    # Create gaussian intensity profile for each particle in local subset
    relative_pts = (pts - np.floor(pts)) + bead_size/2
    f = [0]*nPts
    for i in range(nPts):
        for j in range(nDims):
            f[i] = f[i] - ((m[j] - relative_pts[i,j]) / (2*sigma[i,j]))**2
        f[i] = np.exp(f[i])

    # Compute index location in the original image where the local guassian 
    # subset intensity will be joined/added in the original image
    idx , mask = [[None for _ in range(nPts)] for _ in range(nDims)], [0]*nDims
    for i in range(nDims):
        temp = (np.expand_dims(np.floor(pts[:,i]), axis=1)
                + np.matlib.repmat(np.arange(bead_size[i]), nPts, 1)
                - bead_size[i]/2)
        mask[i] = np.logical_and(temp >=0, temp<sizeI[i])
        for j in range(temp.shape[0]):
            idx[i][j] = temp[j,:].astype(int)
        
        # Find indexes which go outside image frame and crop them
        j_ = np.where(np.any(~mask[i], axis=1))[0].tolist()
        if j_:
            for j in j_:
                if nDims == 2:
                    if i == 0:
                        f[j] = f[j][mask[i][j,:],:]
                    elif i == 1:
                        f[j] = f[j][:,mask[i][j,:]]

                elif nDims == 3:
                    if i == 0:
                        f[j] = f[j][mask[i][j,:],:,:]
                    elif i == 1:
                        f[j] = f[j][:,mask[i][j,:],:]
                    elif i == 2:
                        f[j] = f[j][:,:,mask[i][j,:]]
                
                idx[i][j] = idx[i][j][mask[i][j,:]]
    
    # Add image subset for each particle to the main image
    I = np.zeros(sizeI)
    if nDims == 2:
        for i in range(nPts):
            I[idx[0][i][0]:idx[0][i][-1]+1, 
              idx[1][i][0]:idx[1][i][-1]+1] = np.maximum(
                                                I[idx[0][i][0]:idx[0][i][-1]+1, 
                                                  idx[1][i][0]:idx[1][i][-1]+1], 
                                                f[i])

    elif nDims == 3:        
        for i in range(nPts):            
            I[idx[0][i][0]:idx[0][i][-1]+1, 
              idx[1][i][0]:idx[1][i][-1]+1,
              idx[2][i][0]:idx[2][i][-1]+1] = np.maximum(
                                                I[idx[0][i][0]:idx[0][i][-1]+1, 
                                                  idx[1][i][0]:idx[1][i][-1]+1,
                                                  idx[2][i][0]:idx[2][i][-1]+1], 
                                                f[i])
       
    # Remove saturated pixels
    I[I > 1] = 1
    return I

def random_seed_locations(nPts, sizeI):
    return np.random.random((nPts, len(sizeI)))*sizeI


def add_poisson_noise(I, snr=10):
    return np.random.poisson(I*(snr**2))/(snr**2)


def add_gaussian_noise(I, mean=0, sigma=0.1):
    return I + np.random.normal(mean, sigma, size=I.shape)


def change_im_range(I, lower=0.2, upper=0.8):
    return (I - lower)*(upper-lower) + lower


def create_im(n_images, sizeI, psf, sigma_pts, snr, gauss_noise, im_range):
    '''
    Create bead images for training or testing

    '''
    n_slices = [x for x in range(10)]
    imgs = np.zeros((n_images, sizeI[0], sizeI[1]))
    imgs_noise = np.zeros((n_images, sizeI[0], sizeI[1]))
    for i in range(n_images/n_slices):
        for sigma, nPts in sigma_pts.items():

            # Random number of points and corresponding sigma
            nPts = np.round(np.random.poisson(nPts))
            pts = random_seed_locations(nPts, sizeI)
            sigma = (sigma + np.random.normal(0, 0.2*sigma, size=sigma.shape))
            
            # Create image with random particle info
            img = np.maximum(seedBeadsN(pts, sizeI, sigma), img)

        # Save true images
        imgs[i*n_slices:(i+1)*n_slices,:,:] = img[n_slices,:,:]
        
        # Convole img with a psf
        img = ndimage.convolve(img, psf, mode='constant', cval=0.0)
        imgs_noise[i*n_slices:(i+1)*n_slices,:,:] = imgs_noise[n_slices,:,:]

    for i in range(n_images):
        # Change image intensity distribution
        middle = np.random.random()
        lower = np.random.random()*middle
        upper = np.random.random()*(1-middle) + middle
        imgs_noise[i,:,:] = change_im_range(imgs[i,:,:], lower, upper)


    
    imgs = np.expand_dims(imgs, axis=3)
    imgs_noise = np.expand_dims(imgs_noise, axis=3)


    imgs_noise = add_poisson_noise(imgs, snr)
    imgs_noise = add_gaussian_noise(imgs_noise, 
                                    gauss_noise['mean'], gauss_noise['std'])

    return imgs_noise, imgs