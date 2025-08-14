import Bentodemo from './bentogrid';

export const Features = () => {
  return (

    <div className="bg-black text-white py-[72px] sm:py-24 ">

      <div className="container">
        <h2 className="text-center font-bold text-5xl sm:text-6xl tracking-tighter">Powerful Features for WhatsApp Management</h2>
        <div className='max-w-3xl mx-auto'>
        <p className="text-center mt-5 text-xl text-white/70">
          CuWhapp brings enterprise-grade WhatsApp management to your fingertips with AI-powered automation and comprehensive analytics.
        </p>
        </div>
        <div className="flex flex-col items-center justify-center sm:flex-row gap-4 mt-32">
          <Bentodemo />
          

        </div>

      </div>


    </div>
  )
}
